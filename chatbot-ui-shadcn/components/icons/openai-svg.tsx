// GPT user icon 
// removed svg to remove the icon from the chatbot-ui

import { FC } from "react"
import Image from 'next/image'  // Add this import
import avatarImage from './avatar.jpg'  // Adjust path as needed

interface OpenAISVGProps {
  height?: number
  width?: number
  className?: string
}

export const OpenAISVG: FC<OpenAISVGProps> = ({
  height = 50,
  width = 50,
  className
}) => {
  return (
    <div className="overflow-hidden">
      <Image 
        className={className}
        src={avatarImage}
        width={width}
        height={height}
        alt="Avatar"
        priority
        style={{ objectFit: 'cover' }} 
      />
    </div>
  )
}
