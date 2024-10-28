// export default Chat;
"use client";
import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Form, Button, InputGroup, FormControl, Alert } from 'react-bootstrap';

function Chat() {
  const [messages, setMessages] = useState([
    { sender: 'Counselor', text: 'Hello! How can I assist you today?' }
  ]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);
  const reconnectAttempts = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = window.location.hostname;
    const port = '8000';
    
    const wsUrl = hostname === 'localhost' || hostname === '127.0.0.1'
      ? `${protocol}//${hostname}:${port}/ws`
      : `${protocol}//${hostname}/ws`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log("WebSocket connection established.");
      setIsConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
    };

    ws.current.onmessage = (event) => {
      const newMessage = { sender: 'Counselor', text: event.data };
      setMessages(prev => [...prev, newMessage]);
      scrollToBottom();
    };

    ws.current.onclose = (event) => {
      setIsConnected(false);
      const reason = event.reason || 'No reason provided';
      setError(`WebSocket connection closed. Reason: ${reason}`);
      console.error(`WebSocket closed: ${reason}`);
      handleReconnect();
    };

    ws.current.onerror = (event) => {
      const errorMessage = event.message || 'An unknown error occurred';
      setError(`WebSocket error: ${errorMessage}`);
      console.error(`WebSocket error: ${errorMessage}`);
    };
  };

  const handleReconnect = () => {
    if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts.current += 1;
      console.log(`Attempting to reconnect (${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})`);
      
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      
      reconnectTimeout.current = setTimeout(() => {
        connectWebSocket();
      }, 3000); // Retry every 3 seconds
    } else {
      setError('Maximum reconnection attempts reached. Please refresh the page.');
    }
  };

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close();
        console.log("WebSocket connection closed on component unmount.");
      }
    };
  }, []);

  const sendMessage = () => {
    if (input.trim() === '') return;

    const userMessage = { sender: 'You', text: input };
    setMessages(prev => [...prev, userMessage]);

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(input);
    } else {
      console.error('WebSocket is not open. Ready state:', ws.current?.readyState);
      setError('WebSocket is not connected. Please try reconnecting.');
    }

    setInput('');
    scrollToBottom();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <Container fluid className="vh-100 d-flex flex-column" style={{ backgroundColor: '#f8f9fa' }}>
      <Row className="flex-grow-1">
        <Col className="mx-auto d-flex flex-column">
          <div className="chat-header py-3 text-center">
            <h3 className="font-serif mb-0 fw-bold text-dark">HIV and PrEP Counselor Chatbot</h3>
            <hr style={{ borderColor: '#464544', margin: '15px 20px' }} />
          </div>
          <div className="messages flex-grow-1 p-3" style={{ overflowY: 'scroll' }}>
            {messages.map((msg, index) => (
              <div key={index} className={`message-wrapper d-flex ${msg.sender === 'You' ? 'justify-content-end' : 'justify-content-start'}`}>
                <div className={`message p-2 mb-2 rounded ${msg.sender === 'You' ? 'bg-primary text-white' : 'bg-light border'}`}>
                  {msg.text}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          {!isConnected && (
            <Alert variant="warning" className="m-2">
              WebSocket is disconnected. Attempting to reconnect...
            </Alert>
          )}
          {error && (
            <Alert variant="danger" className="m-2">
              {error}
            </Alert>
          )}
          <Form onSubmit={handleSubmit} className="bg-white p-3">
            <InputGroup>
              <FormControl
                as="textarea"
                rows={2}
                placeholder="Type your message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={!isConnected}
              />
              <Button variant="primary" type="submit" disabled={!isConnected}>
                Send
              </Button>
            </InputGroup>
          </Form>
        </Col>
      </Row>
    </Container>
  );
}

export default Chat;