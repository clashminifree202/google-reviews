import { LoginForm } from '@/components/ui/login-form'
import { SmokeyBackground } from '@/components/ui/smokey-background'

export default function DemoOne() {
  return (
    <main className="relative w-screen h-screen bg-gray-900">
      <SmokeyBackground className="absolute inset-0" />
      <div className="relative z-10 flex items-center justify-center w-full h-full p-4">
        <LoginForm />
      </div>
    </main>
  )
}
