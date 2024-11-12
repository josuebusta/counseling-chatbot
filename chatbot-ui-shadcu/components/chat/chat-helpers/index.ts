// Only used in use-chat-handler.tsx to keep it clean
"use client";
import { createChatFiles } from "@/db/chat-files"
import { createChat } from "@/db/chats"
import { createMessageFileItems } from "@/db/message-file-items"
import { createMessages, updateMessage } from "@/db/messages"
import { uploadMessageImage } from "@/db/storage/message-images"
import {
  buildFinalMessages,
  adaptMessagesForGoogleGemini
} from "@/lib/build-prompt"
import { consumeReadableStream } from "@/lib/consume-stream"
import { Tables, TablesInsert } from "@/supabase/types"
import {
  ChatFile,
  ChatMessage,
  ChatPayload,
  ChatSettings,
  LLM,
  MessageImage
} from "@/types"
import { toast } from "sonner"
import { v4 as uuidv4 } from "uuid"

import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Form, Button, InputGroup, FormControl, Alert } from 'react-bootstrap';




// websocket state addition:
// const [input, setInput] = useState('');
// const [isConnected, setIsConnected] = useState(false);
// const [error, setError] = useState(null);
// const messagesEndRef = useRef(null);
// const ws = useRef(null);
// const reconnectTimeout = useRef(null);
// const reconnectAttempts = useRef(0);
// const MAX_RECONNECT_ATTEMPTS = 5;
// const [isTyping, setIsTyping] = useState(false);

export const validateChatSettings = (
  chatSettings: ChatSettings | null,
  modelData: LLM | undefined,
  profile: Tables<"profiles"> | null,
  selectedWorkspace: Tables<"workspaces"> | null,
  messageContent: string
) => {
  if (!chatSettings) {
    throw new Error("Chat settings not found")
  }

  if (!modelData) {
    throw new Error("Model not found")
  }

  if (!profile) {
    throw new Error("Profile not found")
  }

  if (!selectedWorkspace) {
    throw new Error("Workspace not found")
  }

  if (!messageContent) {
    throw new Error("Message content not found")
  }
}

export const handleRetrieval = async (
  userInput: string,
  newMessageFiles: ChatFile[],
  chatFiles: ChatFile[],
  embeddingsProvider: "openai" | "local",
  sourceCount: number
) => {
  const response = await fetch("/api/retrieval/retrieve", {
    method: "POST",
    body: JSON.stringify({
      userInput,
      fileIds: [...newMessageFiles, ...chatFiles].map(file => file.id),
      embeddingsProvider,
      sourceCount
    })
  })

  if (!response.ok) {
    console.error("Error retrieving:", response)
  }

  const { results } = (await response.json()) as {
    results: Tables<"file_items">[]
  }

  return results
}

export const createTempMessages = (
  messageContent: string,
  chatMessages: ChatMessage[],
  chatSettings: ChatSettings,
  b64Images: string[],
  isRegeneration: boolean,
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  selectedAssistant: Tables<"assistants"> | null
) => {
  let tempUserChatMessage: ChatMessage = {
    message: {
      chat_id: "",
      assistant_id: null,
      content: messageContent,
      created_at: "",
      id: uuidv4(),
      image_paths: b64Images,
      model: chatSettings.model,
      role: "user",
      sequence_number: chatMessages.length,
      updated_at: "",
      user_id: ""
    },
    fileItems: []
  }

  let tempAssistantChatMessage: ChatMessage = {
    message: {
      chat_id: "",
      assistant_id: selectedAssistant?.id || null,
      content: "",
      created_at: "",
      id: uuidv4(),
      image_paths: [],
      model: chatSettings.model,
      role: "assistant",
      sequence_number: chatMessages.length + 1,
      updated_at: "",
      user_id: ""
    },
    fileItems: []
  }

  let newMessages = []

  if (isRegeneration) {
    const lastMessageIndex = chatMessages.length - 1
    chatMessages[lastMessageIndex].message.content = ""
    newMessages = [...chatMessages]
  } else {
    newMessages = [
      ...chatMessages,
      tempUserChatMessage,
      tempAssistantChatMessage
    ]
  }

  setChatMessages(newMessages)

  return {
    tempUserChatMessage,
    tempAssistantChatMessage
  }
}

export const handleLocalChat = async (
  payload: ChatPayload,
  profile: Tables<"profiles">,
  chatSettings: ChatSettings,
  tempAssistantMessage: ChatMessage,
  isRegeneration: boolean,
  newAbortController: AbortController,
  setIsGenerating: React.Dispatch<React.SetStateAction<boolean>>,
  setFirstTokenReceived: React.Dispatch<React.SetStateAction<boolean>>,
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  setToolInUse: React.Dispatch<React.SetStateAction<string>>
) => {
  const formattedMessages = await buildFinalMessages(payload, profile, []);

  const response = await fetchChatResponse(
    process.env.NEXT_PUBLIC_OLLAMA_URL + "/api/chat",
    {
      model: chatSettings.model,
      messages: formattedMessages,
      options: {
        temperature: payload.chatSettings.temperature,
      },
    },
    false,
    newAbortController,
    setIsGenerating,
    setChatMessages
  );

  // Read the response stream and convert it to a string
  let responseText = "";
  if (response.body) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const streamResult = await reader.read();
    responseText = decoder.decode(streamResult.value, { stream: true });
  }

  return await processResponse(
    responseText, // pass the decoded string instead of the stream
    isRegeneration
      ? payload.chatMessages[payload.chatMessages.length - 1]
      : tempAssistantMessage,
    false,
    newAbortController,
    setFirstTokenReceived,
    setChatMessages,
    setToolInUse
  );
};


// export const handleHostedChat = async (
//   payload: ChatPayload,
//   profile: Tables<"profiles">,
//   modelData: LLM,
//   tempAssistantChatMessage: ChatMessage,
//   isRegeneration: boolean,
//   newAbortController: AbortController,
//   newMessageImages: MessageImage[],
//   chatImages: MessageImage[],
//   setIsGenerating: React.Dispatch<React.SetStateAction<boolean>>,
//   setFirstTokenReceived: React.Dispatch<React.SetStateAction<boolean>>,
//   setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
//   setToolInUse: React.Dispatch<React.SetStateAction<string>>
// ) => {
//   const provider =
//     modelData.provider === "openai" && profile.use_azure_openai
//       ? "azure"
//       : modelData.provider

//   let draftMessages = await buildFinalMessages(payload, profile, chatImages)

//   let formattedMessages : any[] = []
//   if (provider === "google") {
//     formattedMessages = await adaptMessagesForGoogleGemini(payload, draftMessages)
//   } else {
//     formattedMessages = draftMessages
//   }

//   const apiEndpoint =
//     provider === "custom" ? "/api/chat/custom" : `/api/chat/${provider}`

//   const requestBody = {
//     chatSettings: payload.chatSettings,
//     messages: formattedMessages,
//     customModelId: provider === "custom" ? modelData.hostedId : ""
//   }

//   const response = await fetchChatResponse(
//     apiEndpoint,
//     requestBody,
//     true,
//     newAbortController,
//     setIsGenerating,
//     setChatMessages
//   )

//   return await processResponse(
//     response,
//     isRegeneration
//       ? payload.chatMessages[payload.chatMessages.length - 1]
//       : tempAssistantChatMessage,
//     true,
//     newAbortController,
//     setFirstTokenReceived,
//     setChatMessages,
//     setToolInUse
//   )
// }

// Persistent WebSocket reference
// Declare the WebSocket variable to be reused across multiple calls
let socket: WebSocket | null = null;

function initializeWebSocket(
  setIsGenerating: React.Dispatch<React.SetStateAction<boolean>>
): WebSocket {
  if (!socket || socket.readyState === WebSocket.CLOSED) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const hostname = window.location.hostname;
    const port = "8000";

    const wsUrl =
      hostname === "localhost" || hostname === "127.0.0.1"
        ? `${protocol}//${hostname}:${port}/ws`
        : `${protocol}//${hostname}:${port}/ws`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("WebSocket connection established");
    };

    socket.onclose = () => {
      console.log("WebSocket connection closed");
      socket = null; // Reset the socket to allow reconnection if closed
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsGenerating(false); // Stop loading in case of error
    };
  }
  return socket;
}

export const handleHostedChat = async (
  payload: ChatPayload,
  profile: Tables<"profiles">,
  modelData: LLM,
  tempAssistantChatMessage: ChatMessage,
  isRegeneration: boolean,
  newAbortController: AbortController,
  newMessageImages: MessageImage[],
  chatImages: MessageImage[],
  setIsGenerating: React.Dispatch<React.SetStateAction<boolean>>,
  setFirstTokenReceived: React.Dispatch<React.SetStateAction<boolean>>,
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  setToolInUse: React.Dispatch<React.SetStateAction<string>>
): Promise<string> => {
  console.log("Received payload:", payload);

  const provider =
    modelData.provider === "openai" && profile.use_azure_openai
      ? "azure"
      : modelData.provider;

  let draftMessages = await buildFinalMessages(payload, profile, chatImages);

  let formattedMessages: any[] = [];
  if (provider === "google") {
    formattedMessages = await adaptMessagesForGoogleGemini(payload, draftMessages);
  } else {
    formattedMessages = draftMessages;
  }

  console.log("Draft messages:", formattedMessages);

  // Build request body
  const requestBody = {
    chatSettings: payload.chatSettings,
    messages: formattedMessages,
    customModelId: provider === "custom" ? modelData.hostedId : "",
  };
  console.log("Request body:", requestBody);

  return new Promise((resolve, reject) => {
    // Ensure WebSocket is initialized
    const ws = initializeWebSocket(setIsGenerating);

    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(requestBody.messages[requestBody.messages.length - 1].content));
      setIsGenerating(true);
    } else {
      ws.onopen = () => {
        ws.send(JSON.stringify(requestBody.messages[requestBody.messages.length - 1].content));
        setIsGenerating(true);
      };
    }

    ws.onmessage = (event) => {
      const response = event.data;
      console.log("response:", response);

      // Handle the response from your custom backend
      processResponse(
        response,
        isRegeneration
          ? payload.chatMessages[payload.chatMessages.length - 1]
          : tempAssistantChatMessage,
        true,
        newAbortController,
        setFirstTokenReceived,
        setChatMessages,
        setToolInUse
      );

      setIsGenerating(false); // Stop the loading indicator once the response is received

      // Resolve the promise with the response (or a part of it)
      resolve(response.message); // Adjust based on the structure of the response
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setIsGenerating(false); // Stop loading in case of error
      reject(error);  // Reject the promise if there's an error
    };
  });
};





export const fetchChatResponse = async (
  url: string,
  body: object,
  isHosted: boolean,
  controller: AbortController,
  setIsGenerating: React.Dispatch<React.SetStateAction<boolean>>,
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
) => {
  const response = await fetch(url, {
    method: "POST",
    body: JSON.stringify(body),
    signal: controller.signal
  })

  if (!response.ok) {
    if (response.status === 404 && !isHosted) {
      toast.error(
        "Model not found. Make sure you have it downloaded via Ollama."
      )
    }

    const errorData = await response.json()

    toast.error(errorData.message)

    setIsGenerating(false)
    setChatMessages(prevMessages => prevMessages.slice(0, -2))
  }

  return response
}


export const processResponse = async (
  response: string,
  lastChatMessage: ChatMessage,
  isHosted: boolean,
  controller: AbortController,
  setFirstTokenReceived: React.Dispatch<React.SetStateAction<boolean>>,
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  setToolInUse: React.Dispatch<React.SetStateAction<string>>
) => {
  let fullText = "";
  let contentToAdd = "";

  // Convert string to ReadableStream<Uint8Array>
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(response));
      controller.close();
    }
  });

  if (stream) {
    await consumeReadableStream(
      stream,
      chunk => {
        setFirstTokenReceived(true);
        setToolInUse("none");

        try {
          contentToAdd = isHosted
            ? chunk
            : // Ollama's streaming endpoint returns new-line separated JSON
              chunk
                .trimEnd()
                .split("\n")
                .reduce(
                  (acc, line) => acc + JSON.parse(line).message.content,
                  ""
                );
          fullText += contentToAdd;
        } catch (error) {
          console.error("Error parsing JSON:", error);
        }

        setChatMessages(prev => [
          ...prev.slice(0, prev.findIndex(msg => msg.message.id === lastChatMessage.message.id)),
          {
            message: {
              ...lastChatMessage.message,
              content: fullText
            },
            fileItems: lastChatMessage.fileItems
          },
          ...prev.slice(prev.findIndex(msg => msg.message.id === lastChatMessage.message.id) + 1)
        ]);
      },
      controller.signal
    );

    return fullText;
  } else {
    throw new Error("Response body is null");
  }
};


export const handleCreateChat = async (
  chatSettings: ChatSettings,
  profile: Tables<"profiles">,
  selectedWorkspace: Tables<"workspaces">,
  messageContent: string,
  selectedAssistant: Tables<"assistants">,
  newMessageFiles: ChatFile[],
  setSelectedChat: React.Dispatch<React.SetStateAction<Tables<"chats"> | null>>,
  setChats: React.Dispatch<React.SetStateAction<Tables<"chats">[]>>,
  setChatFiles: React.Dispatch<React.SetStateAction<ChatFile[]>>
) => {
  const createdChat = await createChat({
    user_id: profile.user_id,
    workspace_id: selectedWorkspace.id,
    assistant_id: selectedAssistant?.id || null,
    context_length: chatSettings.contextLength,
    include_profile_context: chatSettings.includeProfileContext,
    include_workspace_instructions: chatSettings.includeWorkspaceInstructions,
    model: chatSettings.model,
    name: messageContent.substring(0, 100),
    prompt: chatSettings.prompt,
    temperature: chatSettings.temperature,
    embeddings_provider: chatSettings.embeddingsProvider
  })

  setSelectedChat(createdChat)
  setChats(chats => [createdChat, ...chats])

  await createChatFiles(
    newMessageFiles.map(file => ({
      user_id: profile.user_id,
      chat_id: createdChat.id,
      file_id: file.id
    }))
  )

  setChatFiles(prev => [...prev, ...newMessageFiles])

  return createdChat
}

export const handleCreateMessages = async (
  chatMessages: ChatMessage[],
  currentChat: Tables<"chats">,
  profile: Tables<"profiles">,
  modelData: LLM,
  messageContent: string,
  generatedText: string,
  newMessageImages: MessageImage[],
  isRegeneration: boolean,
  retrievedFileItems: Tables<"file_items">[],
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  setChatFileItems: React.Dispatch<
    React.SetStateAction<Tables<"file_items">[]>
  >,
  setChatImages: React.Dispatch<React.SetStateAction<MessageImage[]>>,
  selectedAssistant: Tables<"assistants"> | null
) => {
  const finalUserMessage: TablesInsert<"messages"> = {
    chat_id: currentChat.id,
    assistant_id: null,
    user_id: profile.user_id,
    content: messageContent,
    model: modelData.modelId,
    role: "user",
    sequence_number: chatMessages.length,
    image_paths: []
  }

  const finalAssistantMessage: TablesInsert<"messages"> = {
    chat_id: currentChat.id,
    assistant_id: selectedAssistant?.id || null,
    user_id: profile.user_id,
    content: generatedText,
    model: modelData.modelId,
    role: "assistant",
    sequence_number: chatMessages.length + 1,
    image_paths: []
  }

  let finalChatMessages: ChatMessage[] = []

  if (isRegeneration) {
    const lastStartingMessage = chatMessages[chatMessages.length - 1].message

    const updatedMessage = await updateMessage(lastStartingMessage.id, {
      ...lastStartingMessage,
      content: generatedText
    })

    chatMessages[chatMessages.length - 1].message = updatedMessage

    finalChatMessages = [...chatMessages]

    setChatMessages(finalChatMessages)
  } else {
    const createdMessages = await createMessages([
      finalUserMessage,
      finalAssistantMessage
    ])

    // Upload each image (stored in newMessageImages) for the user message to message_images bucket
    const uploadPromises = newMessageImages
      .filter(obj => obj.file !== null)
      .map(obj => {
        let filePath = `${profile.user_id}/${currentChat.id}/${
          createdMessages[0].id
        }/${uuidv4()}`

        return uploadMessageImage(filePath, obj.file as File).catch(error => {
          console.error(`Failed to upload image at ${filePath}:`, error)
          return null
        })
      })

    const paths = (await Promise.all(uploadPromises)).filter(
      Boolean
    ) as string[]

    setChatImages(prevImages => [
      ...prevImages,
      ...newMessageImages.map((obj, index) => ({
        ...obj,
        messageId: createdMessages[0].id,
        path: paths[index]
      }))
    ])

    const updatedMessage = await updateMessage(createdMessages[0].id, {
      ...createdMessages[0],
      image_paths: paths
    })

    const createdMessageFileItems = await createMessageFileItems(
      retrievedFileItems.map(fileItem => {
        return {
          user_id: profile.user_id,
          message_id: createdMessages[1].id,
          file_item_id: fileItem.id
        }
      })
    )

    finalChatMessages = [
      ...chatMessages,
      {
        message: updatedMessage,
        fileItems: []
      },
      {
        message: createdMessages[1],
        fileItems: retrievedFileItems.map(fileItem => fileItem.id)
      }
    ]

    setChatFileItems(prevFileItems => {
      const newFileItems = retrievedFileItems.filter(
        fileItem => !prevFileItems.some(prevItem => prevItem.id === fileItem.id)
      )

      return [...prevFileItems, ...newFileItems]
    })

    setChatMessages(finalChatMessages)
  }
}


// Only used in use-chat-handler.tsx to keep it clean

// import { createChatFiles } from "@/db/chat-files"
// import { createChat } from "@/db/chats"
// import { createMessageFileItems } from "@/db/message-file-items"
// import { createMessages, updateMessage } from "@/db/messages"
// import { uploadMessageImage } from "@/db/storage/message-images"
// import {
//   buildFinalMessages,
//   adaptMessagesForGoogleGemini
// } from "@/lib/build-prompt"
// import { consumeReadableStream } from "@/lib/consume-stream"
// import { Tables, TablesInsert } from "@/supabase/types"
// import {
//   ChatFile,
//   ChatMessage,
//   ChatPayload,
//   ChatSettings,
//   LLM,
//   MessageImage
// } from "@/types"
// import { toast } from "sonner"
// import { v4 as uuidv4 } from "uuid"
// "use client";
// import React, { useState, useEffect, useRef } from 'react';
// import { Container, Row, Col, Form, Button, InputGroup, FormControl, Alert } from 'react-bootstrap';




// // websocket state addition:
// const [input, setInput] = useState('');
// const [isConnected, setIsConnected] = useState(false);
// const [error, setError] = useState(null);
// const messagesEndRef = useRef(null);
// const ws = useRef(null);
// const reconnectTimeout = useRef(null);
// const reconnectAttempts = useRef(0);
// const MAX_RECONNECT_ATTEMPTS = 5;
// const [isTyping, setIsTyping] = useState(false);


// const connectWebSocket = (
//   ws: React.MutableRefObject<WebSocket | null>,
//   setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
//   setIsConnected: React.Dispatch<React.SetStateAction<boolean>>,
//   setError: React.Dispatch<React.SetStateAction<string | null>>,
//   scrollToBottom: () => void
// ) => {
//   const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
//   const hostname = window.location.hostname;
//   const port = '8000';

//   const wsUrl = `${protocol}//${hostname}:${port}/ws`;

//   ws.current = new WebSocket(wsUrl);

//   ws.current.onopen = () => {
//     console.log("WebSocket connection established!");
//     setIsConnected(true);
//     setError(null);
//   };

//   ws.current.onmessage = (event) => {
//     console.log("Received data:", event.data);

//     let messageData;
//     try {
//       messageData = JSON.parse(event.data);
//     } catch {
//       // Handle non-JSON message as plain text
//       const newMessage: ChatMessage = {
//         sender: 'Counselor',
//         text: event.data,
//         message: { assistant_id: Date.now().toString(), chat_id: event.data }
//       };
//       setChatMessages((prev) => [...prev, newMessage]);
//       scrollToBottom();
//       return;
//     }

//     // JSON message handling
//     if (messageData && typeof messageData.content === 'string') {
//       const newMessage: ChatMessage = {
//         sender: 'Counselor',
//         text: messageData.content,
//         message: { id: Date.now().toString(), content: messageData.content }
//       };
//       setChatMessages((prev) => [...prev, newMessage]);
//       scrollToBottom();
//     }
//   };

//   ws.current.onclose = (event) => {
//     setIsConnected(false);
//     setError(`WebSocket closed: ${event.reason || "No reason provided"}`);
//   };

//   ws.current.onerror = (event) => {
//     setError(`WebSocket error: ${event.data || "Unknown error"}`);
//   };
// };

// export const validateChatSettings = (
//   chatSettings: ChatSettings | null,
//   modelData: LLM | undefined,
//   profile: Tables<"profiles"> | null,
//   selectedWorkspace: Tables<"workspaces"> | null,
//   messageContent: string
// ) => {
//   if (!chatSettings) {
//     throw new Error("Chat settings not found")
//   }

//   if (!modelData) {
//     throw new Error("Model not found")
//   }

//   if (!profile) {
//     throw new Error("Profile not found")
//   }

//   if (!selectedWorkspace) {
//     throw new Error("Workspace not found")
//   }

//   if (!messageContent) {
//     throw new Error("Message content not found")
//   }
// }

// export const handleRetrieval = async (
//   userInput: string,
//   newMessageFiles: ChatFile[],
//   chatFiles: ChatFile[],
//   embeddingsProvider: "openai" | "local",
//   sourceCount: number
// ) => {
//   const response = await fetch("/api/retrieval/retrieve", {
//     method: "POST",
//     body: JSON.stringify({
//       userInput,
//       fileIds: [...newMessageFiles, ...chatFiles].map(file => file.id),
//       embeddingsProvider,
//       sourceCount
//     })
//   })

//   if (!response.ok) {
//     console.error("Error retrieving:", response)
//   }

//   const { results } = (await response.json()) as {
//     results: Tables<"file_items">[]
//   }

//   return results
// }

// export const createTempMessages = (
//   messageContent: string,
//   chatMessages: ChatMessage[],
//   chatSettings: ChatSettings,
//   b64Images: string[],
//   isRegeneration: boolean,
//   setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
//   selectedAssistant: Tables<"assistants"> | null
// ) => {
//   let tempUserChatMessage: ChatMessage = {
//     message: {
//       chat_id: "",
//       assistant_id: null,
//       content: messageContent,
//       created_at: "",
//       id: uuidv4(),
//       image_paths: b64Images,
//       model: chatSettings.model,
//       role: "user",
//       sequence_number: chatMessages.length,
//       updated_at: "",
//       user_id: ""
//     },
//     fileItems: []
//   }

//   let tempAssistantChatMessage: ChatMessage = {
//     message: {
//       chat_id: "",
//       assistant_id: selectedAssistant?.id || null,
//       content: "",
//       created_at: "",
//       id: uuidv4(),
//       image_paths: [],
//       model: chatSettings.model,
//       role: "assistant",
//       sequence_number: chatMessages.length + 1,
//       updated_at: "",
//       user_id: ""
//     },
//     fileItems: []
//   }

//   let newMessages = []

//   if (isRegeneration) {
//     const lastMessageIndex = chatMessages.length - 1
//     chatMessages[lastMessageIndex].message.content = ""
//     newMessages = [...chatMessages]
//   } else {
//     newMessages = [
//       ...chatMessages,
//       tempUserChatMessage,
//       tempAssistantChatMessage
//     ]
//   }

//   setChatMessages(newMessages)

//   return {
//     tempUserChatMessage,
//     tempAssistantChatMessage
//   }
// }

// export const handleLocalChat = async (
//   payload: ChatPayload,
//   profile: Tables<"profiles">,
//   chatSettings: ChatSettings,
//   tempAssistantMessage: ChatMessage,
//   isRegeneration: boolean,
//   newAbortController: AbortController,
//   setIsGenerating: React.Dispatch<React.SetStateAction<boolean>>,
//   setFirstTokenReceived: React.Dispatch<React.SetStateAction<boolean>>,
//   setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
//   setToolInUse: React.Dispatch<React.SetStateAction<string>>
// ) => {
//   const formattedMessages = await buildFinalMessages(payload, profile, [])

//   // Ollama API: https://github.com/jmorganca/ollama/blob/main/docs/api.md
//   const response = await fetchChatResponse(
//     process.env.NEXT_PUBLIC_OLLAMA_URL + "/api/chat",
//     {
//       model: chatSettings.model,
//       messages: formattedMessages,
//       options: {
//         temperature: payload.chatSettings.temperature
//       }
//     },
//     false,
//     newAbortController,
//     setIsGenerating,
//     setChatMessages
//   )

//   return await processResponse(
//     response,
//     isRegeneration
//       ? payload.chatMessages[payload.chatMessages.length - 1]
//       : tempAssistantMessage,
//     false,
//     newAbortController,
//     setFirstTokenReceived,
//     setChatMessages,
//     setToolInUse
//   )
// }

// export const handleHostedChat = async (
//   payload: ChatPayload,
//   profile: Tables<"profiles">,
//   modelData: LLM,
//   tempAssistantChatMessage: ChatMessage,
//   isRegeneration: boolean,
//   newAbortController: AbortController,
//   newMessageImages: MessageImage[],
//   chatImages: MessageImage[],
//   setIsGenerating: React.Dispatch<React.SetStateAction<boolean>>,
//   setFirstTokenReceived: React.Dispatch<React.SetStateAction<boolean>>,
//   setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
//   setToolInUse: React.Dispatch<React.SetStateAction<string>>
// ) => {
//   const provider =
//     modelData.provider === "openai" && profile.use_azure_openai
//       ? "azure"
//       : modelData.provider

//   let draftMessages = await buildFinalMessages(payload, profile, chatImages)

//   let formattedMessages : any[] = []
//   if (provider === "google") {
//     formattedMessages = await adaptMessagesForGoogleGemini(payload, draftMessages)
//   } else {
//     formattedMessages = draftMessages
//   }

//   const apiEndpoint =
//     provider === "custom" ? "/api/chat/custom" : `/api/chat/${provider}`

//   const requestBody = {
//     chatSettings: payload.chatSettings,
//     messages: formattedMessages,
//     customModelId: provider === "custom" ? modelData.hostedId : ""
//   }

//   const response = await fetchChatResponse(
//     apiEndpoint,
//     requestBody,
//     true,
//     newAbortController,
//     setIsGenerating,
//     setChatMessages
//   )

//   return await processResponse(
//     response,
//     isRegeneration
//       ? payload.chatMessages[payload.chatMessages.length - 1]
//       : tempAssistantChatMessage,
//     true,
//     newAbortController,
//     setFirstTokenReceived,
//     setChatMessages,
//     setToolInUse
//   )
// }

// export const fetchChatResponse = async (
//   url: string,
//   body: object,
//   isHosted: boolean,
//   controller: AbortController,
//   setIsGenerating: React.Dispatch<React.SetStateAction<boolean>>,
//   setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
// ) => {
//   const response = await fetch(url, {
//     method: "POST",
//     body: JSON.stringify(body),
//     signal: controller.signal
//   })

//   if (!response.ok) {
//     if (response.status === 404 && !isHosted) {
//       toast.error(
//         "Model not found. Make sure you have it downloaded via Ollama."
//       )
//     }

//     const errorData = await response.json()

//     toast.error(errorData.message)

//     setIsGenerating(false)
//     setChatMessages(prevMessages => prevMessages.slice(0, -2))
//   }

//   return response
// }

// export const processResponse = async (
//   response: Response,
//   lastChatMessage: ChatMessage,
//   isHosted: boolean,
//   controller: AbortController,
//   setFirstTokenReceived: React.Dispatch<React.SetStateAction<boolean>>,
//   setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
//   setToolInUse: React.Dispatch<React.SetStateAction<string>>
// ) => {
//   let fullText = ""
//   let contentToAdd = ""

//   if (response.body) {
//     await consumeReadableStream(
//       response.body,
//       chunk => {
//         setFirstTokenReceived(true)
//         setToolInUse("none")

//         try {
//           contentToAdd = isHosted
//             ? chunk
//             : // Ollama's streaming endpoint returns new-line separated JSON
//               // objects. A chunk may have more than one of these objects, so we
//               // need to split the chunk by new-lines and handle each one
//               // separately.
//               chunk
//                 .trimEnd()
//                 .split("\n")
//                 .reduce(
//                   (acc, line) => acc + JSON.parse(line).message.content,
//                   ""
//                 )
//           fullText += contentToAdd
//         } catch (error) {
//           console.error("Error parsing JSON:", error)
//         }

//         setChatMessages(prev =>
//           prev.map(chatMessage => {
//             if (chatMessage.message.id === lastChatMessage.message.id) {
//               const updatedChatMessage: ChatMessage = {
//                 message: {
//                   ...chatMessage.message,
//                   content: fullText
//                 },
//                 fileItems: chatMessage.fileItems
//               }

//               return updatedChatMessage
//             }

//             return chatMessage
//           })
//         )
//       },
//       controller.signal
//     )

//     return fullText
//   } else {
//     throw new Error("Response body is null")
//   }
// }

// export const handleCreateChat = async (
//   chatSettings: ChatSettings,
//   profile: Tables<"profiles">,
//   selectedWorkspace: Tables<"workspaces">,
//   messageContent: string,
//   selectedAssistant: Tables<"assistants">,
//   newMessageFiles: ChatFile[],
//   setSelectedChat: React.Dispatch<React.SetStateAction<Tables<"chats"> | null>>,
//   setChats: React.Dispatch<React.SetStateAction<Tables<"chats">[]>>,
//   setChatFiles: React.Dispatch<React.SetStateAction<ChatFile[]>>
// ) => {
//   const createdChat = await createChat({
//     user_id: profile.user_id,
//     workspace_id: selectedWorkspace.id,
//     assistant_id: selectedAssistant?.id || null,
//     context_length: chatSettings.contextLength,
//     include_profile_context: chatSettings.includeProfileContext,
//     include_workspace_instructions: chatSettings.includeWorkspaceInstructions,
//     model: chatSettings.model,
//     name: messageContent.substring(0, 100),
//     prompt: chatSettings.prompt,
//     temperature: chatSettings.temperature,
//     embeddings_provider: chatSettings.embeddingsProvider
//   })

//   setSelectedChat(createdChat)
//   setChats(chats => [createdChat, ...chats])

//   await createChatFiles(
//     newMessageFiles.map(file => ({
//       user_id: profile.user_id,
//       chat_id: createdChat.id,
//       file_id: file.id
//     }))
//   )

//   setChatFiles(prev => [...prev, ...newMessageFiles])

//   return createdChat
// }

// export const handleCreateMessages = async (
//   chatMessages: ChatMessage[],
//   currentChat: Tables<"chats">,
//   profile: Tables<"profiles">,
//   modelData: LLM,
//   messageContent: string,
//   generatedText: string,
//   newMessageImages: MessageImage[],
//   isRegeneration: boolean,
//   retrievedFileItems: Tables<"file_items">[],
//   setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
//   setChatFileItems: React.Dispatch<
//     React.SetStateAction<Tables<"file_items">[]>
//   >,
//   setChatImages: React.Dispatch<React.SetStateAction<MessageImage[]>>,
//   selectedAssistant: Tables<"assistants"> | null
// ) => {
//   const finalUserMessage: TablesInsert<"messages"> = {
//     chat_id: currentChat.id,
//     assistant_id: null,
//     user_id: profile.user_id,
//     content: messageContent,
//     model: modelData.modelId,
//     role: "user",
//     sequence_number: chatMessages.length,
//     image_paths: []
//   }

//   const finalAssistantMessage: TablesInsert<"messages"> = {
//     chat_id: currentChat.id,
//     assistant_id: selectedAssistant?.id || null,
//     user_id: profile.user_id,
//     content: generatedText,
//     model: modelData.modelId,
//     role: "assistant",
//     sequence_number: chatMessages.length + 1,
//     image_paths: []
//   }

//   let finalChatMessages: ChatMessage[] = []

//   if (isRegeneration) {
//     const lastStartingMessage = chatMessages[chatMessages.length - 1].message

//     const updatedMessage = await updateMessage(lastStartingMessage.id, {
//       ...lastStartingMessage,
//       content: generatedText
//     })

//     chatMessages[chatMessages.length - 1].message = updatedMessage

//     finalChatMessages = [...chatMessages]

//     setChatMessages(finalChatMessages)
//   } else {
//     const createdMessages = await createMessages([
//       finalUserMessage,
//       finalAssistantMessage
//     ])

//     // Upload each image (stored in newMessageImages) for the user message to message_images bucket
//     const uploadPromises = newMessageImages
//       .filter(obj => obj.file !== null)
//       .map(obj => {
//         let filePath = `${profile.user_id}/${currentChat.id}/${
//           createdMessages[0].id
//         }/${uuidv4()}`

//         return uploadMessageImage(filePath, obj.file as File).catch(error => {
//           console.error(`Failed to upload image at ${filePath}:`, error)
//           return null
//         })
//       })

//     const paths = (await Promise.all(uploadPromises)).filter(
//       Boolean
//     ) as string[]

//     setChatImages(prevImages => [
//       ...prevImages,
//       ...newMessageImages.map((obj, index) => ({
//         ...obj,
//         messageId: createdMessages[0].id,
//         path: paths[index]
//       }))
//     ])

//     const updatedMessage = await updateMessage(createdMessages[0].id, {
//       ...createdMessages[0],
//       image_paths: paths
//     })

//     const createdMessageFileItems = await createMessageFileItems(
//       retrievedFileItems.map(fileItem => {
//         return {
//           user_id: profile.user_id,
//           message_id: createdMessages[1].id,
//           file_item_id: fileItem.id
//         }
//       })
//     )

//     finalChatMessages = [
//       ...chatMessages,
//       {
//         message: updatedMessage,
//         fileItems: []
//       },
//       {
//         message: createdMessages[1],
//         fileItems: retrievedFileItems.map(fileItem => fileItem.id)
//       }
//     ]

//     setChatFileItems(prevFileItems => {
//       const newFileItems = retrievedFileItems.filter(
//         fileItem => !prevFileItems.some(prevItem => prevItem.id === fileItem.id)
//       )

//       return [...prevFileItems, ...newFileItems]
//     })

//     setChatMessages(finalChatMessages)
//   }
// }
