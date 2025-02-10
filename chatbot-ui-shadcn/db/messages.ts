import { supabase } from "@/lib/supabase/browser-client"
import { TablesInsert, TablesUpdate } from "@/supabase/types"
import { Tables } from "@/supabase/types"

export const getMessageById = async (messageId: string) => {
  const { data: message } = await supabase
    .from("messages")
    .select("*")
    .eq("id", messageId)
    .single()

  if (!message) {
    throw new Error("Message not found")
  }

  return message
}

export const getMessagesByChatId = async (chatId: string) => {
  console.log("getMessagesByChatId", chatId)
  const { data: messages } = await supabase
    .from("messages")
    .select("*")
    .eq("chat_id", chatId)
  
  console.log("messages", messages)

  if (!messages) {
    throw new Error("Messages not found")
  }

  return messages
}

export const createMessage = async (message: TablesInsert<"messages">) => {
  const { data: createdMessage, error } = await supabase
    .from("messages")
    .insert([message])
    .select("*")
    .single()

  if (error) {
    throw new Error(error.message)
  }

  return createdMessage
}

// export const createMessages = async (messages: TablesInsert<"messages">[]) => {
  // const { data: createdMessages, error } = await supabase
  //   .from("messages")
  //   .insert(messages)
  //   .select("*")
  //   .maybeSingle() 
//    console.log("createdMessagesfunction", createdMessages)
//   console.log("createdMessagesfunction2")

//   if (!createdMessages) {
//   throw new Error("Failed to create messages - no data returned");
    // }
    // return createdMessages
    // }


  export const createMessages = async (messages: TablesInsert<"messages">[]) => {
  if (!messages?.length) {
    throw new Error("No messages to create")
  }

  messages.forEach(msg => {
    if (!msg.chat_id || !msg.user_id || !msg.content || !msg.role) {
  
      console.error("Invalid message:", msg)
      throw new Error("Invalid message format") 
    }
  })

  const { data, error } = await supabase
    .from("messages")
    .insert(messages)
    .select()

  if (error) {
    console.error("Supabase error:", error)
    throw new Error(`Failed to create messages: ${error.message}`)
  }

  return data
}
  
 
  // if (error) {
  //   throw new Error(`Failed to create messages: ${error.message}`)
  // }

  

export const updateMessage = async (
  messageId: string,
  message: TablesUpdate<"messages">
) => {
  const { data: updatedMessage, error } = await supabase
    .from("messages")
    .update(message)
    .eq("id", messageId)
    .select("*")
    .single()

  if (error) {
    throw new Error(error.message)
  }

  return updatedMessage
}

export const deleteMessage = async (messageId: string) => {
  const { error } = await supabase.from("messages").delete().eq("id", messageId)

  if (error) {
    throw new Error(error.message)
  }

  return true
}

export async function deleteMessagesIncludingAndAfter(
  userId: string,
  chatId: string,
  sequenceNumber: number
) {
  const { error } = await supabase.rpc("delete_messages_including_and_after", {
    p_user_id: userId,
    p_chat_id: chatId,
    p_sequence_number: sequenceNumber
  })

  if (error) {
    return {
      error: "Failed to delete messages."
    }
  }

  return true
}
