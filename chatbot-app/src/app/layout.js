// app/layout.js
import 'bootstrap/dist/css/bootstrap.min.css';
import './globals.css'; // Adjust this path if necessary

export const metadata = {
  title: 'Chatbot App',
  description: 'HIV PrEP Counselor Chatbot',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
