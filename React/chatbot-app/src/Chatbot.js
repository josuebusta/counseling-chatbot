import React, { useEffect, useRef, useState } from 'react';

const Chatbot = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const ws = useRef(null);

    useEffect(() => {
        // Establish WebSocket connection
        ws.current = new WebSocket('ws://localhost:8000/ws/chat'); // Update with your server address

        ws.current.onmessage = (event) => {
            const newMessage = event.data;
            setMessages((prevMessages) => [...prevMessages, newMessage]);
        };

        return () => {
            ws.current.close(); // Close WebSocket on component unmount
        };
    }, []);

    const sendMessage = () => {
        if (input.trim() === '') return;
        ws.current.send(input);
        setMessages((prevMessages) => [...prevMessages, `You: ${input}`]);
        setInput('');
    };

    return (
        <div>
            <h1>HIV PrEP Chatbot</h1>
            <div id="chat-box" style={{ border: '1px solid black', height: '300px', overflowY: 'scroll', padding: '10px' }}>
                {messages.map((msg, index) => (
                    <div key={index}>{msg}</div>
                ))}
            </div>
            <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message here..."
            />
            <button onClick={sendMessage}>Send</button>
        </div>
    );
};

export default Chatbot;
