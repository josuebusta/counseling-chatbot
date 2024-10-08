import React, { useState, useEffect, useRef } from 'react';
import { Container, Row, Col, Form, Button, Card, InputGroup, FormControl, Alert } from 'react-bootstrap';
import './App.css';

function App() {
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

    // On WebSocket open, set the connection state to true
    ws.current.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    // On receiving a message, append it to the messages list
    ws.current.onmessage = (event) => {
      const newMessage = { sender: 'Counselor', text: event.data };
      setMessages(prev => [...prev, newMessage]);
      scrollToBottom();
    };

    // On WebSocket close or error, update the connection state and display an error
    ws.current.onclose = () => {
      setIsConnected(false);
      setError('WebSocket connection closed. Reconnecting...');
    };

    ws.current.onerror = (err) => {
      setError(`WebSocket error: ${err.message}`);
    };

    // Cleanup the WebSocket connection when the component unmounts
    return () => {
      ws.current.close();
    };
  }, []);

  const sendMessage = () => {
    if (input.trim() === '') return; // Prevent sending empty messages

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

    setInput(''); // Clear input field
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
              <Form onSubmit={handleSubmit}>
                <InputGroup>
                  <FormControl
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
            </Card.Footer>
          </Card>
        </Col>
      </Row>
    </Container>
  );
}

export default App;
