import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiClient } from '@/api/client'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

type CallbackStatus = 'processing' | 'success' | 'error'

export function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<CallbackStatus>('processing')
  const [error, setError] = useState<string | null>(null)
  const [characterName, setCharacterName] = useState<string | null>(null)

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')

      if (!code || !state) {
        setStatus('error')
        setError('Missing authentication parameters')
        return
      }

      try {
        const response = await apiClient.get('/auth/callback', {
          params: { code, state }
        })

        setCharacterName(response.data.character_name || 'Character')
        setStatus('success')

        // Redirect to dashboard after 2 seconds
        setTimeout(() => {
          navigate('/', { replace: true })
        }, 2000)
      } catch (err: unknown) {
        setStatus('error')
        const errorMessage = err instanceof Error ? err.message : 'Authentication failed'
        setError(errorMessage)
      }
    }

    handleCallback()
  }, [searchParams, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center gap-4 p-8">
          {status === 'processing' && (
            <>
              <Loader2 className="h-12 w-12 text-primary animate-spin" />
              <h2 className="text-xl font-semibold">Authenticating...</h2>
              <p className="text-sm text-muted-foreground text-center">
                Completing EVE SSO authentication
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="h-12 w-12 text-green-500" />
              <h2 className="text-xl font-semibold">Character Added!</h2>
              <p className="text-sm text-muted-foreground text-center">
                {characterName} has been successfully authenticated.
                <br />
                Redirecting to dashboard...
              </p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="h-12 w-12 text-destructive" />
              <h2 className="text-xl font-semibold">Authentication Failed</h2>
              <p className="text-sm text-muted-foreground text-center">
                {error || 'An error occurred during authentication'}
              </p>
              <Button onClick={() => navigate('/', { replace: true })} className="mt-4">
                Return to Dashboard
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
