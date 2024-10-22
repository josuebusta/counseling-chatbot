export default function handler(req, res) {
  if (req.method === 'POST') {
    const userMessage = req.body.message;
    // Here you would typically process the message and generate a response
    // For now, we'll just echo the message back
    const botResponse = `You said: ${userMessage}`;
    res.status(200).json({ message: botResponse });
  } else {
    res.setHeader('Allow', ['POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}