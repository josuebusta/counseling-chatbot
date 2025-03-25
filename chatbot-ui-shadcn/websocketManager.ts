export class WebSocketManager {
  private static instance: WebSocketManager;
  private socket: WebSocket | null = null;
  private messageQueue: any[] = [];
  private userId: string | null = null;
  private chatId: string | null = null;
  private isInitialized: boolean = false;
  private initializationPromise: Promise<void> | null = null;
  private pendingMessageResolvers: Map<string, (value: any) => void> = new Map();

  private constructor() {}
  public messageProcessing: boolean = false;

  public static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      console.log("Creating new WebSocketManager instance");
      WebSocketManager.instance = new WebSocketManager();
    }
    return WebSocketManager.instance;
  }

  public initializeWithUserId(userId: string): Promise<void> {
    // If already initializing with this user ID, return existing promise
    if (this.initializationPromise && this.userId === userId) {
      return this.initializationPromise;
    }

    this.userId = userId;
    
    this.initializationPromise = new Promise((resolve) => {
      const ws = this.getSocket();
      console.log("isInitialized")
      if (!this.isInitialized) {
        if (ws.readyState === WebSocket.OPEN) {
          console.log("readyState")
          this.sendUserId();
        } else {
          const openHandler = () => {
            console.log("openHandler1")
            this.sendUserId();
            ws.removeEventListener('open', openHandler);

          };
          ws.addEventListener('open', openHandler);
          console.log("openHandler2")
        }
      }
    });
    console.log("initializationPromise", this.initializationPromise)

    return this.initializationPromise;
  }

  private sendUserId() {
    if (!this.userId || !this.socket) return;
    console.log("Sending user ID:", this.userId);
    this.socket.send(JSON.stringify({
      type: 'user_id',
      content: this.userId
    }));

  }

  public initializeWithChatId(chatId: string | null): Promise<void> {
    if (this.initializationPromise && this.chatId === chatId) {
      return this.initializationPromise;
    }

    this.chatId = chatId;
    
    this.initializationPromise = new Promise((resolve) => {
      const ws = this.getSocket();
      console.log("isInitialized")
      if (!this.isInitialized) {
        if (ws.readyState === WebSocket.OPEN) {
          console.log("readyState")
          this.sendChatId();
        } else {
          const openHandler = () => {
            console.log("openHandler1")
            this.sendUserId();
            ws.removeEventListener('open', openHandler);

          };
          ws.addEventListener('open', openHandler);
          console.log("openHandler2")
        }
      }
    });
    console.log("initializationPromise", this.initializationPromise)

    return this.initializationPromise;
  }

  private sendChatId() {
    if (!this.chatId || !this.socket) return;
    console.log("Sending chat ID:", this.chatId);
    this.socket.send(JSON.stringify({
      type: 'chat_id',
      content: this.chatId
    }));

  }

  public async sendTeachabilityFlag(teachabilityFlag: boolean) {
    if (!this.socket) return;
    this.socket.send(JSON.stringify({
      type: 'teachability_flag',
      content: teachabilityFlag
    }));
  }
  

  public getSocket(setIsGenerating?: React.Dispatch<React.SetStateAction<boolean>>): WebSocket {
    if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const hostname = window.location.hostname;
      const port = "8000";

      const wsUrl = hostname === "localhost" || hostname === "127.0.0.1"
        ? `${protocol}//${hostname}:${port}/ws`
        : `${protocol}//${hostname}:${port}/ws`;

      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        console.log("WebSocket connection established");
        // Process any queued messages if we're already initialized
        
        if (this.isInitialized) {
          this.processQueue();
        }
      };
    


        this.initializationPromise = null;


      this.socket.onclose = () => {
        console.log("WebSocket connection closed");
        this.socket = null;
        this.isInitialized = false;
        this.initializationPromise = null;
        
      };

      this.socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        if (setIsGenerating) {
          setIsGenerating(false);
        }
      };
    }
    return this.socket;
  }

  private processQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.sendMessage(message);
      }
    }
  }

  // public async sendChatMessage(content: string): Promise<any> {
  //   if (!this.isInitialized) {
  //     throw new Error('WebSocket not initialized');
  //   }

  //   const messageId = Math.random().toString(36).substring(7);
  //   const message = {
  //     type: 'message',
  //     messageId,
  //     content,
  //     role: 'user'
  //   };

  //   return new Promise((resolve, reject) => {
  //     const timeout = setTimeout(() => {
  //       this.pendingMessageResolvers.delete(messageId);
  //       reject(new Error('Message timeout'));
  //     }, 30000); // 30 second timeout

  //     this.pendingMessageResolvers.set(messageId, (response) => {
  //       clearTimeout(timeout);
  //       resolve(response);
  //     });

  //     this.sendMessage(message);
  //   });
  // }


  private sendMessage(message: any): void {
    if (!this.socket) {
      this.messageQueue.push(message);
      return;
    }

    if (this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else if (this.socket.readyState === WebSocket.CONNECTING) {
      this.messageQueue.push(message);
    } else {
      // Socket is closing or closed
      this.socket = null;
      this.messageQueue.push(message);
      this.getSocket(); // Recreate the socket
    }
  }

  public close() {
    if (this.socket) {
      this.socket.close();
      this.socket.onclose = () => {
        console.log("WebSocket connection closed");
        this.socket = null;
        this.isInitialized = false;
        this.initializationPromise = null;
      };
      this.getSocket();
      
    }
  }
}

    
    
export const wsManager = WebSocketManager.getInstance();