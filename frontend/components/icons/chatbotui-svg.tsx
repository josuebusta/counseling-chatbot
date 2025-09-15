import { FC } from "react"
import Image from "next/image"

interface ChatbotUISVGProps {
  theme: "dark" | "light"
  scale?: number
}

export const ChatbotUISVG: FC<ChatbotUISVGProps> = ({ theme, scale = 1 }) => {
  const logoSrc = theme === "dark" ? "/DARK_BRAND_LOGO.png" : "/LIGHT_BRAND_LOGO.png"
  
  return (
    <Image
      src={logoSrc}
      alt="Counseling Chatbot Logo"
      width={189 * scale}
      height={194 * scale}
      className="object-contain"
    />
  )
}
