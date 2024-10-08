// frontend/src/App.js

import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Form, Button, Card, InputGroup, FormControl, Spinner, Alert } from 'react-bootstrap';
import './App.css';

function App() {
  const [messages, setMessages] = useState([
    { sender: 'Counselor', text: 'Hello! How can I assist you today?' }
  ]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const userId = 'user1'; // Replace with dynamic IDs as needed
  const messagesEndRef = useRef(null);
  const ws = useRef(null); // WebSocket reference

  useEffect(() => {
    // Determine WebSocket protocol based on current page protocol
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.hostname}:8000/ws?user_id=${encodeURIComponent(userId)}`;

    // Initialize WebSocket connection
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      // Optionally, you can send an initial message or authentication token here
    };

    ws.current.onmessage = (event) => {
      console.log('Message from server:', event.data);
      const newMessage = { sender: 'Counselor', text: event.data };
      setMessages(prev => [...prev, newMessage]);
      scrollToBottom();
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected:', event);
      setIsConnected(false);
      if (!event.wasClean) {
        setError('WebSocket connection closed unexpectedly.');
      }
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('WebSocket encountered an error.');
    };

    // Cleanup on component unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [userId]);

  const sendMessage = () => {
    if (input.trim() === '') return;

    // Append user's message to the chat
    const userMessage = { sender: 'You', text: input };
    setMessages(prev => [...prev, userMessage]);

    // Send message via WebSocket
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(input);
    } else {
      console.error('WebSocket is not open');
      setError('WebSocket is not connected. Please try reconnecting.');
    }

    setInput('');
    scrollToBottom();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage();
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <Container className="mt-5">
      <Row className="justify-content-md-center">
        <Col md={8}>
          <Card>
            <Card.Header className="text-center bg-primary text-white">
              <h3>HIV PrEP Counselor Chatbot</h3>
            </Card.Header>
            <Card.Body className="chat-body">
              <div className="messages">
                {messages.map((msg, index) => (
                  <div key={index} className={`message ${msg.sender === 'You' ? 'user-message' : 'bot-message'}`}>
                    <strong>{msg.sender}:</strong> {msg.text}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              {!isConnected && (
                <Alert variant="warning" className="mt-2">
                  WebSocket is disconnected. Messages may not be sent.
                </Alert>
              )}
              {error && (
                <Alert variant="danger" className="mt-2">
                  {error}
                </Alert>
              )}
            </Card.Body>
            <Card.Footer>
              <Form>
                <InputGroup>
                  <FormControl
                    placeholder="Type your message..."
                    aria-label="User message"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={!isConnected}
                  />
                  <Button variant="primary" onClick={sendMessage} disabled={!isConnected}>
                    Send
                  </Button>
                </InputGroup>
              </Form>
            </Card.Footer>
          </Card>
        </Col>
      </Row>
    </Container>
  );
}

export default App;
