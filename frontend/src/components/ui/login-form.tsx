import { useState } from 'react'
import { User, Lock, ArrowRight } from 'lucide-react'
import { SmokeyBackground } from './smokey-background'

export function LoginForm() {
  const [phone, setPhone] = useState('')
  const [name, setName] = useState('')
  const [lastName, setLastName] = useState('')
  const [view, setView] = useState<'login' | 'register'>('login')
  const [message, setMessage] = useState('')

  const handleSubmit = async () => {
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone }),
      })
      const data = await res.json()
      if (data.status === 'new') {
        setView('register')
        setMessage('Crea tu cuenta')
      } else if (data.status === 'confirm') {
        setMessage('¿Eres ' + data.name + '?')
      } else {
        setMessage('Error')
      }
    } catch (e) {
      setMessage('Error')
    }
  }

  const handleRegister = async () => {
    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, first_name: name, last_name: lastName }),
      })
      const data = await res.json()
      if (data.ok) {
        handleSubmit()
      } else {
        setMessage(data.error || 'Error')
      }
    } catch (e) {
      setMessage('Error')
    }
  }

  return (
    <div className="w-full max-w-sm p-8 space-y-6 bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 shadow-2xl">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-white">PlaceID Bot</h2>
        <p className="mt-2 text-sm text-gray-300">Inicia sesión para buscar</p>
      </div>
      {view === 'login' ? (
        <form className="space-y-8" onSubmit={(e) => { e.preventDefault(); handleSubmit() }}>
          <div className="relative z-0">
            <input
              type="tel"
              id="phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="block py-2.5 px-0 w-full text-sm text-white bg-transparent border-0 border-b-2 border-gray-300 appearance-none focus:outline-none focus:ring-0 focus:border-blue-500 peer"
              placeholder=" "
              required
            />
            <label htmlFor="phone" className="absolute text-sm text-gray-300 duration-300 transform -translate-y-6 scale-75 top-3 -z-10 origin-[0] peer-focus:left-0 peer-focus:text-blue-400">
              <User className="inline-block mr-2 -mt-1" size={16} />
              Teléfono
            </label>
          </div>
          <button type="submit" className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold">
            Iniciar Sesión
          </button>
          <p className="text-center text-xs text-gray-400">
            ¿No tienes cuenta?{' '}
            <button type="button" onClick={() => setView('register')} className="font-semibold text-blue-400 hover:text-blue-300">
              Regístrate
            </button>
          </p>
        </form>
      ) : (
        <form className="space-y-8" onSubmit={(e) => { e.preventDefault(); handleRegister() }}>
          <div className="relative z-0">
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="block py-2.5 px-0 w-full text-sm text-white bg-transparent border-0 border-b-2 border-gray-300 appearance-none focus:outline-none focus:ring-0 focus:border-blue-500 peer" placeholder=" " required />
            <label htmlFor="name" className="absolute text-sm text-gray-300 duration-300 transform -translate-y-6 scale-75 top-3 -z-10 origin-[0] peer-focus:left-0 peer-focus:text-blue-400">
              <User className="inline-block mr-2 -mt-1" size={16} />
              Nombre
            </label>
          </div>
          <div className="relative z-0">
            <input type="text" value={lastName} onChange={(e) => setLastName(e.target.value)} className="block py-2.5 px-0 w-full text-sm text-white bg-transparent border-0 border-b-2 border-gray-300 appearance-none focus:outline-none focus:ring-0 focus:border-blue-500 peer" placeholder=" " required />
            <label htmlFor="lastName" className="absolute text-sm text-gray-300 duration-300 transform -translate-y-6 scale-75 top-3 -z-10 origin-[0] peer-focus:left-0 peer-focus:text-blue-400">
              <User className="inline-block mr-2 -mt-1" size={16} />
              Apellidos
            </label>
          </div>
          <button type="submit" className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold">
            Crear Cuenta
          </button>
          {message && <p className="text-center text-sm text-gray-400">{message}</p>}
        </form>
      )}
    </div>
  )
}
