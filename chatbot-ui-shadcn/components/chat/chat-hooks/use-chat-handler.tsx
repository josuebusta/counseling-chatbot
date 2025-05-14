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
    isToolPickerOpen,
    isInitialMessageSent,
    setIsInitialMessageSent,
    chatId,
    setChatId,
  } = useContext(ChatbotUIContext)

  const chatInputRef = useRef<HTMLTextAreaElement>(null)

  const messageAlreadySent = useRef(false);
  let currentChat = selectedChat ? { ...selectedChat } : null
  const response = "Hello, my name is CHIA. I am an AI assistant for HIV counselling. It's nice to meet you. What can I help you with? Please let me know if you would like me to begin with assessing your HIV risk." 

  // // Initialize chat ID when component mounts
  // useEffect(() => {
  //   if (!chatId) {
  //     const initialChatId = uuidv4();
  //     setChatId(initialChatId);
  //     if (profile?.user_id) {
  //       wsManager.initializeWithUserId(profile.user_id);
  //     }
  //     wsManager.initializeWithChatId(initialChatId);
  //   }
  // }, [chatId, profile?.user_id, setChatId]);

  useEffect(() => {
    const handleInitialMessage = async () => {
      console.log("Response received:", response);
      if (chatMessages.length > 0) {
        return;
      }

      console.log("Profile found, setting initial message sent flag");

      if (response === "Hello, my name is CHIA. I am an AI assistant for HIV counselling. It's nice to meet you. What can I help you with? Please let me know if you would like me to begin with assessing your HIV risk.") {
        const tempMessage = {
          message: {
            chat_id: chatId || "",
            assistant_id: selectedAssistant?.id || null,
            content: response,
            created_at: new Date().toISOString(),
            id: chatId || "",
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
        console.log("chatMessages", chatMessages);
      }
    };

    handleInitialMessage();
  }, [isInitialMessageSent, chatId]);

  useEffect(() => {
    if (!isPromptPickerOpen || !isFilePickerOpen || !isToolPickerOpen) {
      chatInputRef.current?.focus()
    }
  }, [isPromptPickerOpen, isFilePickerOpen, isToolPickerOpen])

  const handleNewChat = async () => {
    // First close any existing WebSocket connection
    if (wsManager) {
        wsManager.close();
    }

    // Reset all state
    setIsInitialMessageSent(false);
    setUserInput("");
    setChatMessages([]);
    setSelectedChat(null);
    setChatFileItems([]);
    setIsGenerating(false);
    setFirstTokenReceived(false);
    setChatFiles([]);
    setChatImages([]);
    setNewMessageFiles([]);
    setNewMessageImages([]);
    setShowFilesDisplay(false);
    setIsPromptPickerOpen(false);
    setIsFilePickerOpen(false);
    setSelectedTools([]);
    setToolInUse("none");

    if (!selectedWorkspace) return;

    // Generate new chat ID and initialize WebSocket
    const newChatId = uuidv4();
    setChatId(newChatId);
    
    // Small delay to ensure the old connection is fully closed
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Initialize new WebSocket connection with both user ID and chat ID
    if (profile?.user_id) {
        await wsManager.initializeWithUserId(profile.user_id);
    }
    await wsManager.initializeWithChatId(newChatId);
    setIsInitialMessageSent(true);

    if (selectedAssistant) {
        setChatSettings({
            model: selectedAssistant.model as LLMID,
            prompt: selectedAssistant.prompt,
            temperature: selectedAssistant.temperature,
            contextLength: selectedAssistant.context_length,
            includeProfileContext: selectedAssistant.include_profile_context,
            includeWorkspaceInstructions: selectedAssistant.include_workspace_instructions,
            embeddingsProvider: selectedAssistant.embeddings_provider as "openai" | "local"
        });

        let allFiles = [];
        const assistantFiles = (await getAssistantFilesByAssistantId(selectedAssistant.id)).files;
        allFiles = [...assistantFiles];
        
        const assistantCollections = (await getAssistantCollectionsByAssistantId(selectedAssistant.id)).collections;
        for (const collection of assistantCollections) {
            const collectionFiles = (await getCollectionFilesByCollectionId(collection.id)).files;
            allFiles = [...allFiles, ...collectionFiles];
        }
        
        const assistantTools = (await getAssistantToolsByAssistantId(selectedAssistant.id)).tools;
        setSelectedTools(assistantTools);
        
        setChatFiles(
            allFiles.map(file => ({
                id: file.id,
                name: file.name,
                type: file.type,
                file: null
            }))
        );

        if (allFiles.length > 0) setShowFilesDisplay(true);
    }

    return router.push(`/${selectedWorkspace.id}/chat`);
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
        throw error; 
      });
      console.log("generatedText 0", generatedText)
      
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
          setChatFiles,
          chatId
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

      // check if the chat already exists in the chatMessages array to avoid duplicates
      console.log("handleCreateMessages1")
      if (currentChat) {
        if (currentChat.id == '') {
          return
        }
      }

      console.log("chatMessages", chatMessages)
      console.log("currentChat", currentChat)
      console.log("profile", profile)
      console.log("modelData", modelData)
      console.log("messageContent", messageContent)
      console.log("generatedText 1", generatedText)
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
        selectedAssistant,
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