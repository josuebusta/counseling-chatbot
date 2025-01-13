import { ChatbotUIContext } from "@/context/context"
import { getAssistantCollectionsByAssistantId } from "@/db/assistant-collections"
import { getAssistantFilesByAssistantId } from "@/db/assistant-files"
import { getAssistantToolsByAssistantId } from "@/db/assistant-tools"
import { updateChat } from "@/db/chats"
import { getCollectionFilesByCollectionId } from "@/db/collection-files"
import { deleteMessagesIncludingAndAfter } from "@/db/messages"
import { buildFinalMessages } from "@/lib/build-prompt"
import { Tables } from "@/supabase/types"
import { ChatMessage, ChatPayload, LLMID, ModelProvider } from "@/types"
import { useRouter } from "next/navigation"
import { useContext, useEffect, useRef, useState } from "react"
import { LLM_LIST } from "../../../lib/models/llm/llm-list"
import {
  createTempMessages,
  handleCreateChat,
  handleCreateMessages,
  handleHostedChat,
  // handleRetrieval,
  processResponse,
  validateChatSettings
} from "../chat-helpers"
import { wsManager } from "@/websocketManager"
import { v4 as uuidv4 } from 'uuid';

export const useChatHandler = () => {
  const router = useRouter()

  const {
    userInput,
    chatFiles,
    setUserInput,
    setNewMessageImages,
    profile,
    setIsGenerating,
    setChatMessages,
    setFirstTokenReceived,
    selectedChat,
    selectedWorkspace,
    setSelectedChat,
    setChats,
    setSelectedTools,
    availableLocalModels,
    availableOpenRouterModels,
    abortController,
    setAbortController,
    chatSettings,
    newMessageImages,
    selectedAssistant,
    chatMessages,
    chatImages,
    setChatImages,
    setChatFiles,
    setNewMessageFiles,
    setShowFilesDisplay,
    newMessageFiles,
    chatFileItems,
    setChatFileItems,
    setToolInUse,
    useRetrieval,
    sourceCount,
    setIsPromptPickerOpen,
    setIsFilePickerOpen,
    selectedTools,
    selectedPreset,
    setChatSettings,
    models,
    isPromptPickerOpen,
    isFilePickerOpen,
    isToolPickerOpen
  } = useContext(ChatbotUIContext)

  const chatInputRef = useRef<HTMLTextAreaElement>(null)
  
  const [isInitialMessageSent, setIsInitialMessageSent] = useState(false);
  const messageAlreadySent = useRef(false);


useEffect(() => {
  // const ws = wsManager.getSocket();
  
  const handleInitialMessage = async () => {
    // const response = event.data;
    const response = "Hello, my name is CHIA. It's nice to meet you. What's your name? If you have already given me your name, what can I help you with?" 
    console.log("Response received:", response);
    if (isInitialMessageSent) return;

    if (!chatMessages.length) {
      console.log("Passes here")
      if (response === "Hello, my name is CHIA. It's nice to meet you. What's your name? If you have already given me your name, what can I help you with?") {

      
      
      const tempMessage = {
        message: {
          chat_id: "",
          assistant_id: selectedAssistant?.id || null,
          content: response,
          created_at: new Date().toISOString(),
          id: uuidv4(),
          image_paths: [],
          model: chatSettings?.model || "default",
          role: "assistant",
          sequence_number: 0,
          updated_at: new Date().toISOString(),
          user_id: profile?.user_id || ""
        },
        fileItems: []
      };
      
      setChatMessages([tempMessage]);
    
      // const newChat = await handleCreateChat(
      //   chatSettings!,
      //   profile!,
      //   selectedWorkspace!,
      //   "Initial Chat",
      //   selectedAssistant!,
      //   [],
      //   setSelectedChat,
      //   setChats,
      //   setChatFiles
      // );

      // await handleCreateMessages(
      //   [tempMessage],
      //   newChat,
      //   profile!,
      //   LLM_LIST[0],
      //   response,
      //   response,
      //   [],
      //   false,
      //   [],
      //   setChatMessages,
      //   setChatFileItems,
      //   setChatImages,
      //   selectedAssistant
      // );
      setIsInitialMessageSent(true);
    }
    }
  };

  // ws.addEventListener('message', handleInitialMessage);
  // return () => ws.removeEventListener('message', handleInitialMessage);
  handleInitialMessage()
}, []);

  useEffect(() => {
    if (!isPromptPickerOpen || !isFilePickerOpen || !isToolPickerOpen) {
      chatInputRef.current?.focus()
    }
  }, [isPromptPickerOpen, isFilePickerOpen, isToolPickerOpen])

  const handleNewChat = async () => {
    if (!selectedWorkspace) return

    setUserInput("")
    setChatMessages([])
    setSelectedChat(null)
    setChatFileItems([])

    setIsGenerating(false)
    setFirstTokenReceived(false)

    setChatFiles([])
    setChatImages([])
    setNewMessageFiles([])
    setNewMessageImages([])
    setShowFilesDisplay(false)
    setIsPromptPickerOpen(false)
    setIsFilePickerOpen(false)

    setSelectedTools([])
    setToolInUse("none")

    if (selectedAssistant) {
      setChatSettings({
        model: selectedAssistant.model as LLMID,
        prompt: selectedAssistant.prompt,
        temperature: selectedAssistant.temperature,
        contextLength: selectedAssistant.context_length,
        includeProfileContext: selectedAssistant.include_profile_context,
        includeWorkspaceInstructions:
          selectedAssistant.include_workspace_instructions,
        embeddingsProvider: selectedAssistant.embeddings_provider as
          | "openai"
          | "local"
      })

      let allFiles = []

      const assistantFiles = (
        await getAssistantFilesByAssistantId(selectedAssistant.id)
      ).files
      allFiles = [...assistantFiles]
      const assistantCollections = (
        await getAssistantCollectionsByAssistantId(selectedAssistant.id)
      ).collections
      for (const collection of assistantCollections) {
        const collectionFiles = (
          await getCollectionFilesByCollectionId(collection.id)
        ).files
        allFiles = [...allFiles, ...collectionFiles]
      }
      const assistantTools = (
        await getAssistantToolsByAssistantId(selectedAssistant.id)
      ).tools

      setSelectedTools(assistantTools)
      setChatFiles(
        allFiles.map(file => ({
          id: file.id,
          name: file.name,
          type: file.type,
          file: null
        }))
      )

      if (allFiles.length > 0) setShowFilesDisplay(true)

    } 
    return router.push(`/${selectedWorkspace.id}/chat`)
  }

  const handleFocusChatInput = () => {
    chatInputRef.current?.focus()
  }

  const handleStopMessage = () => {
    if (abortController) {
      abortController.abort()
    }
  }



const handleSendMessage = async (
    messageContent: string,
    chatMessages: ChatMessage[],
    isRegeneration: boolean
  ) => {
    const startingInput = messageContent
    console.log("handleSendMessage")

    // if (chatMessages.some(msg => msg.message.content === messageContent)) {
    //   console.log("Message already exists, skipping send");
    //   return;
    // }

    try {
      console.log("handleSendMessage3")
      
      setUserInput("")
      setIsGenerating(true)
      setIsPromptPickerOpen(false)
      setIsFilePickerOpen(false)
      setNewMessageImages([])

      console.log("handleSendMessage4")

      const newAbortController = new AbortController()
      setAbortController(newAbortController)

      console.log("handleSendMessage5")

      const modelData = [
        ...models.map(model => ({
          modelId: model.model_id as LLMID,
          modelName: model.name,
          provider: "custom" as ModelProvider,
          hostedId: model.id,
          platformLink: "",
          imageInput: false
        })),
        ...LLM_LIST,
        ...availableLocalModels,
        ...availableOpenRouterModels
      ].find(llm => llm.modelId === chatSettings?.model)


      console.log("handleSendMessage6")

      let currentChat = selectedChat ? { ...selectedChat } : null

      const b64Images = newMessageImages.map(image => image.base64)

      let retrievedFileItems: Tables<"file_items">[] = []

      if (
        (newMessageFiles.length > 0 || chatFiles.length > 0) &&
        useRetrieval
      ) {
        setToolInUse("retrieval")

      }

      const { tempUserChatMessage, tempAssistantChatMessage } =
        createTempMessages(
          messageContent,
          chatMessages,
          chatSettings!,
          b64Images,
          isRegeneration,
          setChatMessages,
          selectedAssistant
        )

      let payload: ChatPayload = {
        chatSettings: chatSettings!,
        workspaceInstructions: selectedWorkspace!.instructions || "",
        chatMessages: isRegeneration
          ? [...chatMessages]
          : [...chatMessages, tempUserChatMessage],
        assistant: selectedChat?.assistant_id ? selectedAssistant : null,
        messageFileItems: retrievedFileItems,
        chatFileItems: chatFileItems
      }

      console.log("currentChat", currentChat)
      let generatedText = ""
      console.log("selectedTools")
      console.log("selectedTools", selectedTools)
      console.log("handleSendMessage9")
      console.log("Profile1")
      generatedText = await handleHostedChat(
        payload,
        profile!,
        modelData!,
        tempAssistantChatMessage,
        isRegeneration,
        newAbortController,
        newMessageImages,
        chatImages,
        setIsGenerating,
        setFirstTokenReceived,
        setChatMessages,
        setToolInUse
      ).catch(error => {
  console.error("handleHostedChat error:", error);
  throw error; // Re-throw to be caught by the outer try-catch
});
console.log("generatedText", generatedText)

  

      if (!currentChat) {
        console.log("currentChat0")
        currentChat = await handleCreateChat(
          chatSettings!,
          profile!,
          selectedWorkspace!,
          messageContent,
          selectedAssistant!,
          newMessageFiles,
          setSelectedChat,
          setChats,
          setChatFiles
        )
        console.log("currentChat1", currentChat)
      } else {
        console.log("currentChat2", currentChat)
        const updatedChat = await updateChat(currentChat.id, {
          updated_at: new Date().toISOString()
        })
        console.log("updatedChat", updatedChat)
        setChats(prevChats => {
          const updatedChats = prevChats.map(prevChat =>
            prevChat.id === updatedChat.id ? updatedChat : prevChat
          )
          console.log("updatedChats", updatedChats)
          return updatedChats
        })
      }

      console.log("handleCreateMessages1")

      console.log("chatMessages", chatMessages)
      console.log("currentChat", currentChat)
      console.log("profile", profile)
      console.log("modelData", modelData)
      console.log("messageContent", messageContent)
      console.log("generatedText", generatedText)
      console.log("newMessageImages", newMessageImages)
      console.log("isRegeneration", isRegeneration)
      console.log("retrievedFileItems", retrievedFileItems)
      await handleCreateMessages(
        chatMessages,
        currentChat,
        profile!,
        modelData!,
        messageContent,
        generatedText,
        newMessageImages,
        isRegeneration,
        retrievedFileItems,
        setChatMessages,
        setChatFileItems,
        setChatImages,
        selectedAssistant
      )

      setIsGenerating(false)
      setFirstTokenReceived(false)
    } catch (error) {
      setIsGenerating(false)
      setFirstTokenReceived(false)
      setUserInput(startingInput)
    }
  }

  const handleSendEdit = async (
    editedContent: string,
    sequenceNumber: number
  ) => {
    if (!selectedChat) return

    await deleteMessagesIncludingAndAfter(
      selectedChat.user_id,
      selectedChat.id,
      sequenceNumber
    )

    const filteredMessages = chatMessages.filter(
      chatMessage => chatMessage.message.sequence_number < sequenceNumber
    )

    setChatMessages(filteredMessages)

    handleSendMessage(editedContent, filteredMessages, false)
  }

  return {
    chatInputRef,
    prompt,
    handleNewChat,
    handleSendMessage,
    handleFocusChatInput,
    handleStopMessage,
    handleSendEdit
  }
}