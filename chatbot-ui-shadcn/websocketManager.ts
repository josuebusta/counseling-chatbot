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
    this.userId = userId;
    
    this.initializationPromise = new Promise((resolve) => {
      const ws = this.getSocket();
      if (ws.readyState === WebSocket.OPEN) {
        this.sendUserId();
        if (this.chatId) {
          this.sendChatId();
        }
        resolve();
      } else {
        const openHandler = () => {
          this.sendUserId();
          if (this.chatId) {
            this.sendChatId();
          }
          ws.removeEventListener('open', openHandler);
          resolve();
        };
        ws.addEventListener('open', openHandler);
      }
    });

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
    this.chatId = chatId;
    
    this.initializationPromise = new Promise((resolve) => {
      const ws = this.getSocket();
      if (ws.readyState === WebSocket.OPEN) {
        if (this.userId) {
          this.sendUserId();
        }
        this.sendChatId();
        resolve();
      } else {
        const openHandler = () => {
          if (this.userId) {
            this.sendUserId();
          }
          this.sendChatId();
          ws.removeEventListener('open', openHandler);
          resolve();
        };
        ws.addEventListener('open', openHandler);
      }
    });

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
        if (this.isInitialized) {
          this.processQueue();
        }
      };

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
      this.socket = null;
      this.messageQueue.push(message);
      this.getSocket();
    }
  }

  public close() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.isInitialized = false;
      this.initializationPromise = null;
      this.chatId = null;
      this.userId = null;
      this.messageQueue = [];
    }
  }
}

export const wsManager = WebSocketManager.getInstance();