import { ChatbotUIContext } from "@/context/context"
import {
  PROFILE_CONTEXT_MAX,
  PROFILE_DISPLAY_NAME_MAX,
  PROFILE_USERNAME_MAX,
  PROFILE_USERNAME_MIN
} from "@/db/limits"
import { updateProfile } from "@/db/profile"
import { uploadProfileImage } from "@/db/storage/profile-images"
import { exportLocalStorageAsJSON } from "@/lib/export-old-data"
// import { fetchOpenRouterModels } from "@/lib/models/fetch-models"
import { LLM_LIST_MAP } from "@/lib/models/llm/llm-list"
import { supabase } from "@/lib/supabase/browser-client"
import { cn } from "@/lib/utils"
import { OpenRouterLLM } from "@/types"
import { useChatHandler } from "../chat/chat-hooks/use-chat-handler"
import { v4 as uuidv4 } from 'uuid';



import {
  IconCircleCheckFilled,
  IconCircleXFilled,
  IconFileDownload,
  IconLoader2,
  IconLogout,
  IconUser
} from "@tabler/icons-react"
import Image from "next/image"
import { useRouter } from "next/navigation"
import { FC, useCallback, useContext, useRef, useState, useEffect } from "react"
import { toast } from "sonner"
import { SIDEBAR_ICON_SIZE } from "../sidebar/sidebar-switcher"
import { Button } from "../ui/button"
import ImagePicker from "../ui/image-picker"
import { Input } from "../ui/input"
import { Label } from "../ui/label"
import { LimitDisplay } from "../ui/limit-display"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger
} from "../ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs"
import { TextareaAutosize } from "../ui/textarea-autosize"
import { WithTooltip } from "../ui/with-tooltip"
import { ThemeSwitcher } from "./theme-switcher"
import { wsManager } from '@/websocketManager';
import { Switch } from "@/components/ui/switch"

interface ProfileSettingsProps {}



export const ProfileSettings: FC<ProfileSettingsProps> = ({}) => {
  const {
    profile,
    setProfile,
    envKeyMap,
    setAvailableHostedModels,
    setAvailableOpenRouterModels,
    availableOpenRouterModels
  } = useContext(ChatbotUIContext)
  
  const router = useRouter()
  const buttonRef = useRef<HTMLButtonElement>(null)
  const [isOpen, setIsOpen] = useState(false)

  // All state declarations needed for the component
  const [displayName, setDisplayName] = useState("")
  const [username, setUsername] = useState("")
  const [usernameAvailable, setUsernameAvailable] = useState(true)
  const [loadingUsername, setLoadingUsername] = useState(false)
  const [profileImageSrc, setProfileImageSrc] = useState("")
  const [profileImageFile, setProfileImageFile] = useState<File | null>(null)
  const [profileInstructions, setProfileInstructions] = useState("")
  
  const [useAzureOpenai, setUseAzureOpenai] = useState(false)
  const [openaiAPIKey, setOpenaiAPIKey] = useState("")
  const [openaiOrgID, setOpenaiOrgID] = useState("")
  const [azureOpenaiAPIKey, setAzureOpenaiAPIKey] = useState("")
  const [azureOpenaiEndpoint, setAzureOpenaiEndpoint] = useState("")
  const [azureOpenai35TurboID, setAzureOpenai35TurboID] = useState("")
  const [azureOpenai45TurboID, setAzureOpenai45TurboID] = useState("")
  const [azureOpenai45VisionID, setAzureOpenai45VisionID] = useState("")
  const [azureEmbeddingsID, setAzureEmbeddingsID] = useState("")
  const [anthropicAPIKey, setAnthropicAPIKey] = useState("")
  const [googleGeminiAPIKey, setGoogleGeminiAPIKey] = useState("")
  const [mistralAPIKey, setMistralAPIKey] = useState("")
  const [groqAPIKey, setGroqAPIKey] = useState("")
  const [perplexityAPIKey, setPerplexityAPIKey] = useState("")
  const [openrouterAPIKey, setOpenrouterAPIKey] = useState("")
  const [teachabilityFlag, setTeachabilityFlag] = useState(() => {
  
    const storedTeachabilityFlag = localStorage.getItem('teachabilityFlag')
    return storedTeachabilityFlag !== null 
      ? JSON.parse(storedTeachabilityFlag) 
      : true
  })

  console.log("Component mounted")

  // Initialize profile data
useEffect(() => {
  console.log("useEffect1")
  let mounted = true

  const initializeProfile = async () => {
    try {
      console.log("initializeProfile1")
      const { data: { session } } = await supabase.auth.getSession()
      console.log("initializeProfile2", session)
      
      if (!session?.user?.id) {
        console.log('No authenticated user')
        router.push("/login")
        return
      }
      console.log("initializeProfile3")
      wsManager.initializeWithUserId(session.user.id); // removed await
      const chatId = uuidv4();
      wsManager.initializeWithChatId(chatId);
      console.log("initializeProfile4")

      // // Initialize WebSocket manager with user ID
      // wsManager.initializeWithUserId(session.user.id);
      // const ws = wsManager.getSocket();
      // ws.send(JSON.stringify({
      //   type: 'user_id',
      //   content: session.user.id
      // }));
      console.log("session.user.id", session.user.id)
      console.log("Querying for user ID:", session.user.id)
      // Fetch profile data for authenticated user
      // let { data: profileData, error } = await supabase
      //   .from('profiles')
      //   .select()  // List specific columns
      //   .match({ id: session.user.id })  // Use match instead of eq
      //   .maybeSingle() 
      // console.log("profileData", profileData)
      // console.log("mounted", mounted)

      console.log("session.user.id", session.user.id)
console.log("Querying for user ID:", session.user.id)

    // Check if id exists in correct format
    if (!session.user.id) {
      console.error("Invalid user ID format");
      return;
    }

    // Add explicit error logging
    let { data: profileData, error } = await supabase
      .from('profiles')
      .select('*')  
      .or(`id.eq.${session.user.id},user_id.eq.${session.user.id}`) 
      .maybeSingle();

    console.log("Query result:", { profileData, error });

    if (error) {
      console.error("Supabase query error:", error);
      return;
    }

//     if (!profileData) {
//   console.log("No profile found - creating new profile");
//   const { data: newProfile, error: createError } = await supabase
//     .from('profiles')
//     .insert({
//       anthropic_api_key: null,
//       azure_openai_35_turbo_id: null,
//       azure_openai_45_turbo_id: null,
//       azure_openai_45_vision_id: null,
//       azure_openai_api_key: null,
//       azure_openai_embeddings_id: null,
//       azure_openai_endpoint: null,
//       bio: '',
//       created_at: new Date().toISOString(),
//       display_name: session.user.email?.split('@')[0] || 'User',
//       google_gemini_api_key: null,
//       groq_api_key: null,
//       has_onboarded: false,
//       id: session.user.id,
//       image_path: '',
//       image_url: '',
//       mistral_api_key: null,
//       openai_api_key: null,
//       openai_organization_id: null,
//       openrouter_api_key: null,
//       perplexity_api_key: null,
//       profile_context: '',
//       updated_at: new Date().toISOString(),
//       use_azure_openai: false,
//       user_id: session.user.id,
//       username: session.user.email?.split('@')[0] || 'user'
//     })
//     .select()
//     .single();

//   if (createError) {
//     console.error("Error creating profile:", createError);
//     return;
//   }

//   profileData = newProfile;
// }
    console.log("Final profileData:", profileData);
      

        if (mounted && profileData) {
          console.log("Setting profile:", profileData)
          setProfile(profileData)
          
          // Initialize all local state with profile data
          setDisplayName(profileData.display_name || "")
          setUsername(profileData.username || "")
          setProfileImageSrc(profileData.image_url || "")
          setProfileInstructions(profileData.profile_context || "")
          setUseAzureOpenai(profileData.use_azure_openai || false)
          setOpenaiAPIKey(profileData.openai_api_key || "")
          setOpenaiOrgID(profileData.openai_organization_id || "")
          setAzureOpenaiAPIKey(profileData.azure_openai_api_key || "")
          setAzureOpenaiEndpoint(profileData.azure_openai_endpoint || "")
          setAzureOpenai35TurboID(profileData.azure_openai_35_turbo_id || "")
          setAzureOpenai45TurboID(profileData.azure_openai_45_turbo_id || "")
          setAzureOpenai45VisionID(profileData.azure_openai_45_vision_id || "")
          setAzureEmbeddingsID(profileData.azure_openai_embeddings_id || "")
          setAnthropicAPIKey(profileData.anthropic_api_key || "")
          setGoogleGeminiAPIKey(profileData.google_gemini_api_key || "")
          setMistralAPIKey(profileData.mistral_api_key || "")
          setGroqAPIKey(profileData.groq_api_key || "")
          setPerplexityAPIKey(profileData.perplexity_api_key || "")
          setOpenrouterAPIKey(profileData.openrouter_api_key || "")
        }
      } catch (error) {
        console.error('Error initializing profile:', error)
      }
    }

    initializeProfile()

    console.log("useEffect2")

    // Set up auth state change listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log("Auth state changed:", event)
        if (event === 'SIGNED_IN' && session?.user?.id) {
          console.log("Signing in")
          initializeProfile()
        } else if (event === 'SIGNED_OUT') {
          if (mounted) {
            setProfile(null)
            router.push("/login")
          }
        }
      }
    )

    return () => {
      mounted = false
      subscription?.unsubscribe()
    }
  }, [setProfile, router])


    const [isInitialMessageSent, setIsInitialMessageSent] = useState(false);

        // Modified useEffect
        // Add this near your other useEffects

  const { handleSendMessage } = useChatHandler();
  const { chatSettings, selectedWorkspace } = useContext(ChatbotUIContext);
  const [hasInitialized, setHasInitialized] = useState(false);


//   useEffect(() => {
//   const autoSendHello = async () => {
//     if (!chatSettings || !selectedWorkspace || hasInitialized) return
    
//     try {
//       console.log("Auto-sending hello message")
//       await handleSendMessage("Hello!", [], false)
//       setHasInitialized(true)
//     } catch (error) {
//       console.error("Error auto-sending hello:", error)
//     }
//   }

//   autoSendHello()
// }, [chatSettings, selectedWorkspace, hasInitialized])

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    setProfile(null)
    router.push("/login")
    router.refresh()
  }

  const debounce = (func: (...args: any[]) => void, wait: number) => {
    let timeout: NodeJS.Timeout | null

    return (...args: any[]) => {
      const later = () => {
        if (timeout) clearTimeout(timeout)
        func(...args)
      }

      if (timeout) clearTimeout(timeout)
      timeout = setTimeout(later, wait)
    }
  }

  const checkUsernameAvailability = useCallback(
    debounce(async (username: string) => {
      if (!username) return

      if (username.length < PROFILE_USERNAME_MIN) {
        setUsernameAvailable(false)
        return
      }

      if (username.length > PROFILE_USERNAME_MAX) {
        setUsernameAvailable(false)
        return
      }

      const usernameRegex = /^[a-zA-Z0-9_]+$/
      if (!usernameRegex.test(username)) {
        setUsernameAvailable(false)
        toast.error(
          "Username must be letters, numbers, or underscores only - no other characters or spacing allowed."
        )
        return
      }

      setLoadingUsername(true)

      const response = await fetch(`/api/username/available`, {
        method: "POST",
        body: JSON.stringify({ username })
      })

      const data = await response.json()
      const isAvailable = data.isAvailable

      setUsernameAvailable(isAvailable)

      if (username === profile?.username) {
        setUsernameAvailable(true)
      }

      setLoadingUsername(false)
    }, 500),
    [profile?.username]
  )

  const handleSave = async () => {
    if (!profile) return;
    let profileImageUrl = profile.image_url;
    let profileImagePath = "";

    if (profileImageFile) {
      const { path, url } = await uploadProfileImage(profile, profileImageFile);
      profileImageUrl = url ?? profileImageUrl;
      profileImagePath = path;
    }

    // Update profile in database
    const updatedProfile = await updateProfile(profile.id, {
      ...profile,
      display_name: displayName,
      username,
      profile_context: profileInstructions,
      image_url: profileImageUrl,
      image_path: profileImagePath,
      openai_api_key: openaiAPIKey,
      openai_organization_id: openaiOrgID,
      anthropic_api_key: anthropicAPIKey,
      google_gemini_api_key: googleGeminiAPIKey,
      mistral_api_key: mistralAPIKey,
      groq_api_key: groqAPIKey,
      perplexity_api_key: perplexityAPIKey,
      use_azure_openai: useAzureOpenai,
      azure_openai_api_key: azureOpenaiAPIKey,
      azure_openai_endpoint: azureOpenaiEndpoint,
      azure_openai_35_turbo_id: azureOpenai35TurboID,
      azure_openai_45_turbo_id: azureOpenai45TurboID,
      azure_openai_45_vision_id: azureOpenai45VisionID,
      azure_openai_embeddings_id: azureEmbeddingsID,
      openrouter_api_key: openrouterAPIKey,
    });

    // After successful profile update:
    setProfile(updatedProfile);
    
    // Update localStorage and send to backend only after successful save
    localStorage.setItem('teachabilityFlag', JSON.stringify(teachabilityFlag));
    // await wsManager.sendTeachabilityFlag(teachabilityFlag);
    
    toast.success("Profile updated!");
    setIsOpen(false);
    setTimeout(() => {
      window.location.reload();
    }, 100);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter") {
      buttonRef.current?.click()
    }
  }

 useEffect(() => {
    console.log("Visibility conditions:", {
      hasProfile: !!profile,
      profileData: profile,
      isSheetOpen: isOpen
    })
  }, [profile, isOpen])

  // if (!profile) return null

  // Add this useEffect to send teachability state when component mounts
  useEffect(() => {
    // Get initial state from localStorage
    const storedTeachabilityFlag = localStorage.getItem('teachabilityFlag');
    const initialState = storedTeachabilityFlag !== null 
      ? JSON.parse(storedTeachabilityFlag) 
      : true;
    
    // Set initial state
    setTeachabilityFlag(initialState);
    
    // Send to backend
    const sendInitialState = async () => {
      try {
        await wsManager.sendTeachabilityFlag(initialState);
        console.log("[INIT] Sent initial teachability state:", initialState);
      } catch (error) {
        console.error("Error sending initial teachability state:", error);
      }
    };

    // Send when WebSocket is ready
    const ws = wsManager.getSocket();
    if (ws.readyState === WebSocket.OPEN) {
      sendInitialState();
    } else {
      ws.addEventListener('open', sendInitialState);
    }

    return () => {
      ws.removeEventListener('open', sendInitialState);
    };
  }, []);

  const handleTeachabilityToggle = async (checked: boolean) => {
    // Only update the local state, don't send to backend yet
    setTeachabilityFlag(checked);
  };

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        {profile?.image_url ? (
          <Image
            className="mt-2 size-[34px] cursor-pointer rounded hover:opacity-50"
            src={profile?.image_url + "?" + new Date().getTime()}
            height={34}
            width={34}
            alt={"Image"}
          />
        ) : (
          <Button size="icon" variant="ghost">
            <IconUser size={SIDEBAR_ICON_SIZE} />
          </Button>
        )}
      </SheetTrigger>

      <SheetContent
        className="flex flex-col justify-between"
        side="left"
        onKeyDown={handleKeyDown}
      >
        <div className="grow overflow-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center justify-between space-x-2">
              <div>User Settings</div>

              <Button
                tabIndex={-1}
                className="text-xs"
                size="sm"
                onClick={handleSignOut}
              >
                <IconLogout className="mr-1" size={20} />
                Logout
              </Button>
            </SheetTitle>
          </SheetHeader>

          <Tabs defaultValue="profile">
            <TabsList className="mt-4 grid w-full grid-cols-2">
              <TabsTrigger value="profile">Profile</TabsTrigger>
              {/* <TabsTrigger value="keys">API Keys</TabsTrigger> */}
            </TabsList>

            <TabsContent className="mt-4 space-y-4" value="profile">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <Label>Username</Label>

                  <div className="text-xs">
                    {username !== profile?.username ? (
                      usernameAvailable ? (
                        <div className="text-green-500">AVAILABLE</div>
                      ) : (
                        <div className="text-red-500">UNAVAILABLE</div>
                      )
                    ) : null}
                  </div>
                </div>

                <div className="relative">
                  <Input
                    className="pr-10"
                    placeholder="Username..."
                    value={username}
                    onChange={e => {
                      setUsername(e.target.value)
                      checkUsernameAvailability(e.target.value)
                    }}
                    minLength={PROFILE_USERNAME_MIN}
                    maxLength={PROFILE_USERNAME_MAX}
                  />

                  {username !== profile?.username ? (
                    <div className="absolute inset-y-0 right-0 flex items-center pr-3">
                      {loadingUsername ? (
                        <IconLoader2 className="animate-spin" />
                      ) : usernameAvailable ? (
                        <IconCircleCheckFilled className="text-green-500" />
                      ) : (
                        <IconCircleXFilled className="text-red-500" />
                      )}
                    </div>
                  ) : null}
                </div>

                <LimitDisplay
                  used={username.length}
                  limit={PROFILE_USERNAME_MAX}
                />
              </div>

              <div className="space-y-1">
                <Label>Profile Image</Label>

                <ImagePicker
                  src={profileImageSrc}
                  image={profileImageFile}
                  height={50}
                  width={50}
                  onSrcChange={setProfileImageSrc}
                  onImageChange={setProfileImageFile}
                />
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <Label>Memory Enabled</Label>
                  <div className="flex space-x-2">
                    <Button
                      size="sm"
                      className={`w-16 ${
                        teachabilityFlag 
                          ? "bg-green-500 hover:bg-green-600 text-white font-bold" 
                          : "bg-gray-100 text-gray-500"
                      }`}
                      onClick={() => handleTeachabilityToggle(true)}
                    >
                      ON
                    </Button>
                    <Button
                      size="sm"
                      className={`w-16 ${
                        !teachabilityFlag 
                          ? "bg-red-500 hover:bg-red-600 text-white font-bold" 
                          : "bg-gray-100 text-gray-500"
                      }`}
                      onClick={() => handleTeachabilityToggle(false)}
                    >
                      OFF
                    </Button>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  When enabled, the AI will remember information from your conversations
                </p>
              </div>

              <div className="space-y-1">
                <Label>Chat Display Name</Label>

                <Input
                  placeholder="Chat display name..."
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  maxLength={PROFILE_DISPLAY_NAME_MAX}
                />
              </div>

              {/* <div className="space-y-1">
                <Label className="text-sm">
                  What would you like the AI to know about you to provide better
                  responses?
                </Label>

                <TextareaAutosize
                  value={profileInstructions}
                  onValueChange={setProfileInstructions}
                  placeholder="Profile context... (optional)"
                  minRows={6}
                  maxRows={10}
                />

                <LimitDisplay
                  used={profileInstructions.length}
                  limit={PROFILE_CONTEXT_MAX}
                />
              </div> */}
            </TabsContent>

            <TabsContent className="mt-4 space-y-4" value="keys">
              <div className="mt-5 space-y-2">
                <Label className="flex items-center">
                  {useAzureOpenai
                    ? envKeyMap["azure"]
                      ? ""
                      : "Azure OpenAI API Key"
                    : envKeyMap["openai"]
                      ? ""
                      : "OpenAI API Key"}

                  <Button
                    className={cn(
                      "h-[18px] w-[150px] text-[11px]",
                      (useAzureOpenai && !envKeyMap["azure"]) ||
                        (!useAzureOpenai && !envKeyMap["openai"])
                        ? "ml-3"
                        : "mb-3"
                    )}
                    onClick={() => setUseAzureOpenai(!useAzureOpenai)}
                  >
                    {useAzureOpenai
                      ? "Switch To Standard OpenAI"
                      : "Switch To Azure OpenAI"}
                  </Button>
                </Label>

                {useAzureOpenai ? (
                  <>
                    {envKeyMap["azure"] ? (
                      <Label>Azure OpenAI API key set by admin.</Label>
                    ) : (
                      <Input
                        placeholder="Azure OpenAI API Key"
                        type="password"
                        value={azureOpenaiAPIKey}
                        onChange={e => setAzureOpenaiAPIKey(e.target.value)}
                      />
                    )}
                  </>
                ) : (
                  <>
                    {envKeyMap["openai"] ? (
                      <Label>OpenAI API key set by admin.</Label>
                    ) : (
                      <Input
                        placeholder="OpenAI API Key"
                        type="password"
                        value={openaiAPIKey}
                        onChange={e => setOpenaiAPIKey(e.target.value)}
                      />
                    )}
                  </>
                )}
              </div>

              <div className="ml-8 space-y-3">
                {useAzureOpenai ? (
                  <>
                    {
                      <div className="space-y-1">
                        {envKeyMap["azure_openai_endpoint"] ? (
                          <Label className="text-xs">
                            Azure endpoint set by admin.
                          </Label>
                        ) : (
                          <>
                            <Label>Azure Endpoint</Label>

                            <Input
                              placeholder="https://your-endpoint.openai.azure.com"
                              value={azureOpenaiEndpoint}
                              onChange={e =>
                                setAzureOpenaiEndpoint(e.target.value)
                              }
                            />
                          </>
                        )}
                      </div>
                    }

                    {
                      <div className="space-y-1">
                        {envKeyMap["azure_gpt_35_turbo_name"] ? (
                          <Label className="text-xs">
                            Azure GPT-3.5 Turbo deployment name set by admin.
                          </Label>
                        ) : (
                          <>
                            <Label>Azure GPT-3.5 Turbo Deployment Name</Label>

                            <Input
                              placeholder="Azure GPT-3.5 Turbo Deployment Name"
                              value={azureOpenai35TurboID}
                              onChange={e =>
                                setAzureOpenai35TurboID(e.target.value)
                              }
                            />
                          </>
                        )}
                      </div>
                    }

                    {
                      <div className="space-y-1">
                        {envKeyMap["azure_gpt_45_turbo_name"] ? (
                          <Label className="text-xs">
                            Azure GPT-4.5 Turbo deployment name set by admin.
                          </Label>
                        ) : (
                          <>
                            <Label>Azure GPT-4.5 Turbo Deployment Name</Label>

                            <Input
                              placeholder="Azure GPT-4.5 Turbo Deployment Name"
                              value={azureOpenai45TurboID}
                              onChange={e =>
                                setAzureOpenai45TurboID(e.target.value)
                              }
                            />
                          </>
                        )}
                      </div>
                    }

                    {
                      <div className="space-y-1">
                        {envKeyMap["azure_gpt_45_vision_name"] ? (
                          <Label className="text-xs">
                            Azure GPT-4.5 Vision deployment name set by admin.
                          </Label>
                        ) : (
                          <>
                            <Label>Azure GPT-4.5 Vision Deployment Name</Label>

                            <Input
                              placeholder="Azure GPT-4.5 Vision Deployment Name"
                              value={azureOpenai45VisionID}
                              onChange={e =>
                                setAzureOpenai45VisionID(e.target.value)
                              }
                            />
                          </>
                        )}
                      </div>
                    }

                    {
                      <div className="space-y-1">
                        {envKeyMap["azure_embeddings_name"] ? (
                          <Label className="text-xs">
                            Azure Embeddings deployment name set by admin.
                          </Label>
                        ) : (
                          <>
                            <Label>Azure Embeddings Deployment Name</Label>

                            <Input
                              placeholder="Azure Embeddings Deployment Name"
                              value={azureEmbeddingsID}
                              onChange={e =>
                                setAzureEmbeddingsID(e.target.value)
                              }
                            />
                          </>
                        )}
                      </div>
                    }
                  </>
                ) : (
                  <>
                    <div className="space-y-1">
                      {envKeyMap["openai_organization_id"] ? (
                        <Label className="text-xs">
                          OpenAI Organization ID set by admin.
                        </Label>
                      ) : (
                        <>
                          <Label>OpenAI Organization ID</Label>

                          <Input
                            placeholder="OpenAI Organization ID (optional)"
                            disabled={
                              !!process.env.NEXT_PUBLIC_OPENAI_ORGANIZATION_ID
                            }
                            type="password"
                            value={openaiOrgID}
                            onChange={e => setOpenaiOrgID(e.target.value)}
                          />
                        </>
                      )}
                    </div>
                  </>
                )}
              </div>

              <div className="space-y-1">
                {envKeyMap["anthropic"] ? (
                  <Label>Anthropic API key set by admin.</Label>
                ) : (
                  <>
                    <Label>Anthropic API Key</Label>
                    <Input
                      placeholder="Anthropic API Key"
                      type="password"
                      value={anthropicAPIKey}
                      onChange={e => setAnthropicAPIKey(e.target.value)}
                    />
                  </>
                )}
              </div>

              <div className="space-y-1">
                {envKeyMap["google"] ? (
                  <Label>Google Gemini API key set by admin.</Label>
                ) : (
                  <>
                    <Label>Google Gemini API Key</Label>
                    <Input
                      placeholder="Google Gemini API Key"
                      type="password"
                      value={googleGeminiAPIKey}
                      onChange={e => setGoogleGeminiAPIKey(e.target.value)}
                    />
                  </>
                )}
              </div>

              <div className="space-y-1">
                {envKeyMap["mistral"] ? (
                  <Label>Mistral API key set by admin.</Label>
                ) : (
                  <>
                    <Label>Mistral API Key</Label>
                    <Input
                      placeholder="Mistral API Key"
                      type="password"
                      value={mistralAPIKey}
                      onChange={e => setMistralAPIKey(e.target.value)}
                    />
                  </>
                )}
              </div>

              <div className="space-y-1">
                {envKeyMap["groq"] ? (
                  <Label>Groq API key set by admin.</Label>
                ) : (
                  <>
                    <Label>Groq API Key</Label>
                    <Input
                      placeholder="Groq API Key"
                      type="password"
                      value={groqAPIKey}
                      onChange={e => setGroqAPIKey(e.target.value)}
                    />
                  </>
                )}
              </div>

              <div className="space-y-1">
                {envKeyMap["perplexity"] ? (
                  <Label>Perplexity API key set by admin.</Label>
                ) : (
                  <>
                    <Label>Perplexity API Key</Label>
                    <Input
                      placeholder="Perplexity API Key"
                      type="password"
                      value={perplexityAPIKey}
                      onChange={e => setPerplexityAPIKey(e.target.value)}
                    />
                  </>
                )}
              </div>

              <div className="space-y-1">
                {envKeyMap["openrouter"] ? (
                  <Label>OpenRouter API key set by admin.</Label>
                ) : (
                  <>
                    <Label>OpenRouter API Key</Label>
                    <Input
                      placeholder="OpenRouter API Key"
                      type="password"
                      value={openrouterAPIKey}
                      onChange={e => setOpenrouterAPIKey(e.target.value)}
                    />
                  </>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </div>

        <div className="mt-6 flex items-center">
          <div className="flex items-center space-x-1">
            <ThemeSwitcher />

            <WithTooltip
              display={
                <div>
                  Download Chatbot UI 1.0 data as JSON. Import coming soon!
                </div>
              }
              trigger={
                <IconFileDownload
                  className="cursor-pointer hover:opacity-50"
                  size={32}
                  onClick={exportLocalStorageAsJSON}
                />
              }
            />
          </div>

          <div className="ml-auto space-x-2">
            <Button variant="ghost" onClick={() => setIsOpen(false)}>
              Cancel
            </Button>

            <Button ref={buttonRef} onClick={handleSave}>
              Save
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

