export class WebSocketManager {
  private static instance: WebSocketManager;
  private socket: WebSocket | null = null;
  private messageQueue: any[] = [];
  private userId: string | null = null;
  private chatId: string | null = null;
  private isInitialized: boolean = false;
  private initializationPromise: Promise<void> | null = null;
  private pendingMessageResolvers: Map<string, (value: any) => void> = new Map();
  private isConnecting: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 3;
  private reconnectDelay: number = 1000;

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

  public initializeWithIds(userId: string, chatId: string): Promise<void> {
    this.userId = userId;
    this.chatId = chatId;
    
    this.initializationPromise = new Promise((resolve) => {
      const ws = this.getSocket();
      if (ws.readyState === WebSocket.OPEN) {
        this.sendUserId();
        this.sendChatId();
        resolve();
      } else {
        const openHandler = () => {
          this.sendUserId();
          this.sendChatId();
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

  public updateChatId(chatId: string) {
    this.chatId = chatId;
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.sendChatId();
    }
  }
  

  public getSocket(setIsGenerating?: React.Dispatch<React.SetStateAction<boolean>>): WebSocket {
    // Return existing socket if it's open or connecting
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return this.socket;
    }

    // Prevent multiple simultaneous connection attempts
    if (this.isConnecting) {
      console.log("WebSocket connection already in progress, waiting...");
      return this.socket || this.createConnection(setIsGenerating);
    }

    return this.createConnection(setIsGenerating);
  }

  private createConnection(setIsGenerating?: React.Dispatch<React.SetStateAction<boolean>>): WebSocket {
    if (this.isConnecting) {
      console.log("Connection already in progress");
      return this.socket!;
    }

    this.isConnecting = true;
    this.reconnectAttempts = 0;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const hostname = window.location.hostname;
    const port = "8000";

    const wsUrl = hostname === "localhost" || hostname === "127.0.0.1"
      ? `${protocol}//${hostname}:${port}/ws`
      : `${protocol}//${hostname}:${port}/ws`;

    console.log("Creating new WebSocket connection to:", wsUrl);
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log("WebSocket connection established");
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.isInitialized = true;
      this.processQueue();
    };

    this.socket.onclose = (event) => {
      console.log("WebSocket connection closed", event.code, event.reason);
      this.isConnecting = false;
      this.isInitialized = false;
      this.initializationPromise = null;
      
      // Only attempt reconnection if it wasn't a clean close
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.attemptReconnection(setIsGenerating);
      } else {
        this.socket = null;
      }
    };

    this.socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      this.isConnecting = false;
      if (setIsGenerating) {
        setIsGenerating(false);
      }
    };

    return this.socket;
  }

  private attemptReconnection(setIsGenerating?: React.Dispatch<React.SetStateAction<boolean>>) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log("Max reconnection attempts reached");
      this.socket = null;
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms`);
    
    setTimeout(() => {
      if (this.reconnectAttempts <= this.maxReconnectAttempts) {
        this.createConnection(setIsGenerating);
      }
    }, this.reconnectDelay);
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
      console.log("Closing WebSocket connection");
      this.socket.close(1000, "Client closing connection");
      this.socket = null;
    }
    
    // Reset all state
    this.isInitialized = false;
    this.initializationPromise = null;
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.chatId = null;
    this.userId = null;
    this.messageQueue = [];
    this.pendingMessageResolvers.clear();
  }

  public isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }

  public getConnectionState(): string {
    if (!this.socket) return 'CLOSED';
    switch (this.socket.readyState) {
      case WebSocket.CONNECTING: return 'CONNECTING';
      case WebSocket.OPEN: return 'OPEN';
      case WebSocket.CLOSING: return 'CLOSING';
      case WebSocket.CLOSED: return 'CLOSED';
      default: return 'UNKNOWN';
    }
  }
}

export const wsManager = WebSocketManager.getInstance();