'use server'

import { createClient } from "@/lib/supabase/server"
import { cookies, headers } from "next/headers"
import { redirect } from "next/navigation"
import { get } from "@vercel/edge-config"

interface SignUpResponse {
  success: boolean;
  message: string;
}

const getEnvVarOrEdgeConfigValue = async (name: string) => {
  if (process.env.EDGE_CONFIG) {
    return await get<string>(name)
  }
  return process.env[name]
}

export async function handleSignUp(formData: FormData): Promise<SignUpResponse> {
  const email = formData.get("email") as string
  const password = formData.get("password") as string
  const origin = headers().get("origin") || ""

  const emailDomainWhitelistPatternsString = await getEnvVarOrEdgeConfigValue(
    "EMAIL_DOMAIN_WHITELIST"
  )
  const emailDomainWhitelist = emailDomainWhitelistPatternsString?.trim()
    ? emailDomainWhitelistPatternsString?.split(",")
    : []
  const emailWhitelistPatternsString =
    await getEnvVarOrEdgeConfigValue("EMAIL_WHITELIST")
  const emailWhitelist = emailWhitelistPatternsString?.trim()
    ? emailWhitelistPatternsString?.split(",")
    : []

  if (emailDomainWhitelist.length > 0 || emailWhitelist.length > 0) {
    const domainMatch = emailDomainWhitelist?.includes(email.split("@")[1])
    const emailMatch = emailWhitelist?.includes(email)
    if (!domainMatch && !emailMatch) {
      return {
        success: false,
        message: `Email ${email} is not allowed to sign up.`
      }
    }
  }

  const cookieStore = cookies()
  const supabase = createClient(cookieStore)

  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${origin}/auth/callback`
    }
  })

  if (error) {
    return {
      success: false,
      message: error.message
    }
  }

  return { 
    success: true, 
    message: "Check email to continue sign in process" 
  }
}