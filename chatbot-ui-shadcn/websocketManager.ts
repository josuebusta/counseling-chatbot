export class WebSocketManager {
  private static instance: WebSocketManager;
  private socket: WebSocket | null = null;
  private messageQueue: any[] = [];
  private userId: string | null = null;
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
      
      const initHandler = (event: MessageEvent) => {
        try {
          const response = JSON.parse(event.data);
          if (response.type === 'connection_established') {
            this.isInitialized = true;
            ws.removeEventListener('message', initHandler);
            resolve();
          }
        } catch (e) {
          console.error('Error parsing init response:', e);
        }
      };

      ws.addEventListener('message', initHandler);
      
      // Only send user ID if not already initialized
      if (!this.isInitialized) {
        if (ws.readyState === WebSocket.OPEN) {
          this.sendUserId();
        } else {
          const openHandler = () => {
            this.sendUserId();
            ws.removeEventListener('open', openHandler);
          };
          ws.addEventListener('open', openHandler);
        }
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

  public async sendChatMessage(content: string): Promise<any> {
    if (!this.isInitialized) {
      throw new Error('WebSocket not initialized');
    }

    const messageId = Math.random().toString(36).substring(7);
    const message = {
      type: 'message',
      messageId,
      content
    };

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingMessageResolvers.delete(messageId);
        reject(new Error('Message timeout'));
      }, 30000); // 30 second timeout

      this.pendingMessageResolvers.set(messageId, (response) => {
        clearTimeout(timeout);
        resolve(response);
      });

      this.sendMessage(message);
    });
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
      // Socket is closing or closed
      this.socket = null;
      this.messageQueue.push(message);
      this.getSocket(); // Recreate the socket
    }
  }

  public close(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this.isInitialized = false;
      this.initializationPromise = null;
      this.pendingMessageResolvers.clear();
      this.messageQueue = [];
    }
  }
}

    
    
export const wsManager = WebSocketManager.getInstance();