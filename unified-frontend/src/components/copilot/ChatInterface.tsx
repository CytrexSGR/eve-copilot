import { Play, AlertCircle, Loader2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Alert, AlertDescription } from '../ui/alert'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { useCopilot } from '../../contexts/CopilotContext'
import { useCharacterContext } from '../../contexts/CharacterContext'

export function ChatInterface() {
  const {
    session,
    messages,
    isStreaming,
    isLoading,
    error,
    sendMessage,
    startSession,
  } = useCopilot()

  const { selectedCharacter, isLoading: isLoadingCharacters } = useCharacterContext()

  // Build portrait URL from character ID
  const characterPortrait = selectedCharacter
    ? `https://images.evetech.net/characters/${selectedCharacter.character_id}/portrait?size=64`
    : undefined

  // Determine button state
  const canStartSession = !isLoading && !isLoadingCharacters && !!selectedCharacter

  // No session state: show start session prompt
  if (!session) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <CardTitle>Start a Session</CardTitle>
            <CardDescription>
              Begin a new AI Copilot session to get help with your EVE Online activities.
              The copilot can assist with market analysis, production planning, skill
              recommendations, and more.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            {error && (
              <Alert variant="destructive" className="w-full">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            {isLoadingCharacters && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading characters...
              </div>
            )}
            {!isLoadingCharacters && !selectedCharacter && (
              <p className="text-sm text-muted-foreground">
                No character selected. Please select a character first.
              </p>
            )}
            <Button onClick={() => startSession()} disabled={!canStartSession}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Start Session
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Active session: show chat interface
  return (
    <div className="flex flex-col h-full">
      <MessageList messages={messages} characterPortrait={characterPortrait} />
      <MessageInput
        onSend={sendMessage}
        isLoading={isStreaming}
        disabled={!session}
        placeholder="Ask the AI Copilot anything..."
      />
    </div>
  )
}
