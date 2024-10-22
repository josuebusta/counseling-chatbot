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
  const ws = useRef(null); // WebSocket reference

  useEffect(() => {
    // Initialize WebSocket connection
    ws.current = new WebSocket('ws://localhost:8000/ws');

    ws.current.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.current.onmessage = (event) => {
      const newMessage = { sender: 'Counselor', text: event.data };
      setMessages(prev => [...prev, newMessage]);
      scrollToBottom();
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      setError('WebSocket connection closed. Reconnecting...');
    };

    ws.current.onerror = (err) => {
      setError(`WebSocket error: ${err.message}`);
    };

    return () => {
      ws.current.close();
    };
  }, []);

  const sendMessage = () => {
    if (input.trim() === '') return;

    const userMessage = { sender: 'You', text: input };
    setMessages(prev => [...prev, userMessage]);

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(input);
    } else {
      console.error('WebSocket is not open');
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
    if (e.key === 'Enter') {
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
          <hr style={{ borderColor: '#464544', margin: '15px 20px' }} /> {/* Divider line */}
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
        {/* Warning message */}
        {!isConnected && (
          <Alert variant="warning" className="m-2 mb-2" style={{ marginLeft: '40px', marginRight: '80px', marginBottom: '50px' }}>
            WebSocket is disconnected. Messages may not be sent.
          </Alert>
        )}
        {/* Error message */}
        {error && (
          <Alert variant="danger" className="m-2 mb-2" style={{ marginLeft: '40px', marginRight: '80px', marginBottom: '50px' }}>
            {error}
          </Alert>
        )}
        {/* Input Form */}
        <Form onSubmit={handleSubmit} className="bg-white" style={{ marginLeft: '40px', marginRight: '80px', marginBottom: '100px' }}>
          <InputGroup>
            <FormControl
              as="textarea"
              rows={2}
              placeholder="Type your message..."
              aria-label="User message"
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
