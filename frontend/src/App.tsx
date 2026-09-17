import { useState } from 'react'
import { apiLogin, apiRegister, apiConfirm } from './api'

export function App() {
  const [view, setView] = useState<'login' | 'register' | 'redeem' | 'main'>('login')
  const [phone, setPhone] = useState('')
  const [name, setName] = useState('')
  const [lastName, setLastName] = useState('')
  const [password, setPassword] = useState('')
  const [key, setKey] = useState('')
  const [webhook, setWebhook] = useState('')
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState<'new' | 'confirm' | 'ok' | 'error'>('ok')
  const [userName, setUserName] = useState('')

  const handleLogin = async () => {
    try {
      const res = await apiLogin(phone)
      if (res.status === 'new') {
        setStatus('new')
        setView('register')
      } else if (res.status === 'confirm') {
        setStatus('confirm')
        setUserName(res.name)
      } else {
        setMessage('Error')
      }
    } catch (e) {
      setMessage('Error de conexión')
    }
  }

  const handleRegister = async () => {
    try {
      const res = await apiRegister(phone, name, lastName)
      if (res.ok) {
        handleConfirm()
      } else {
        setMessage(res.error || 'Error')
      }
    } catch (e) {
      setMessage('Error de conexión')
    }
  }

  const handleConfirm = async () => {
    try {
      const res = await apiConfirm(phone)
      if (res.ok) {
        setStatus('ok')
        setView('main')
      } else {
        setMessage('Teléfono no registrado')
      }
    } catch (e) {
      setMessage('Error')
    }
  }

  const handleRedeem = async () => {
    try {
      const res = await apiRedeem(key, name, lastName, phone, webhook)
      if (res.ok) {
        setMessage('✅ Licencia activada: ' + res.key)
      } else {
        setMessage('❌ ' + res.error)
      }
    } catch (e) {
      setMessage('Error')
    }
  }

  if (view === 'main') {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <h1 className="text-3xl font-bold mb-6 text-center bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            PlaceID Bot
          </h1>
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-6 space-y-4">
            <p className="text-white">Bienvenido, {userName || phone}</p>
            <a href="/canjear" onClick={() => setView('redeem')} className="block w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold text-center cursor-pointer">
              Canjear Licencia
            </a>
            <button onClick={() => setView('login')} className="w-full py-3 bg-white/10 hover:bg-white/20 rounded-lg text-white font-semibold">
              Cambiar Cuenta
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (view === 'redeem') {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="w-full max-w-sm">
          <h2 className="text-3xl font-bold mb-6 text-center text-white">Canjear Licencia</h2>
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-8 space-y-4">
            <input
              type="text"
              placeholder="Licencia (RBL-...)"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="w-full p-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400"
            />
            <input
              type="text"
              placeholder="Nombre"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400"
            />
            <input
              type="text"
              placeholder="Apellidos"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full p-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400"
            />
            <input
              type="tel"
              placeholder="Teléfono"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full p-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400"
            />
            <input
              type="text"
              placeholder="Webhook (opcional)"
              value={webhook}
              onChange={(e) => setWebhook(e.target.value)}
              className="w-full p-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400"
            />
            <button
              onClick={handleRedeem}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold"
            >
              Canjear
            </button>
            {message && <p className="text-center text-sm">{message}</p>}
            {status === 'ok' && (
              <div className="text-center mt-4">
                <div className="text-4xl mb-2">✅</div>
                <h3 className="text-xl font-bold text-green-400">Licencia Activa</h3>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (status === 'confirm') {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="w-full max-w-sm">
          <h2 className="text-3xl font-bold mb-6 text-center text-white">Confirmar</h2>
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-8 space-y-4 text-center">
            <p className="text-white">¿Eres <span className="font-bold text-blue-400">{userName}</span>?</p>
            <button
              onClick={handleConfirm}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold"
            >
              Sí, soy yo
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (status === 'new') {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
        <div className="w-full max-w-sm">
          <h2 className="text-3xl font-bold mb-6 text-center text-white">Crear Cuenta</h2>
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-8 space-y-4">
            <input
              type="text"
              placeholder="Nombre"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400"
            />
            <input
              type="text"
              placeholder="Apellidos"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full p-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400"
            />
            <button
              onClick={handleRegister}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold"
            >
              Crear Cuenta
            </button>
            {message && <p className="text-center text-sm text-red-400">{message}</p>}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h2 className="text-3xl font-bold mb-6 text-center text-white">PlaceID Bot</h2>
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl border border-white/20 p-8 space-y-4">
          <div className="relative z-0">
            <input
              type="tel"
              placeholder=" "
              id="phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="block py-2.5 px-0 w-full text-sm text-white bg-transparent border-0 border-b-2 border-gray-300 appearance-none focus:outline-none focus:ring-0 focus:border-blue-500 peer"
              required
            />
            <label
              htmlFor="phone"
              className="absolute text-sm text-gray-300 duration-300 transform -translate-y-6 scale-75 top-3 -z-10 origin-[0] peer-focus:left-0 peer-focus:text-blue-400"
            >
              📱 Teléfono
            </label>
          </div>
          <button
            onClick={handleLogin}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold"
          >
            Iniciar Sesión
          </button>
          <p className="text-center text-xs text-gray-400">
            ¿No tienes cuenta? <button onClick={() => { setStatus('new'); setView('register') }} className="font-semibold text-blue-400 hover:text-blue-300">Regístrate</button>
          </p>
        </div>
      </div>
    </div>
  )
}

async function apiLogin(phone: string) {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  })
  return res.json()
}

async function apiRegister(phone: string, firstName: string, lastName: string) {
  const res = await fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, first_name: firstName, last_name: lastName }),
  })
  return res.json()
}

async function apiConfirm(phone: string) {
  const res = await fetch('/api/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  })
  return res.json()
}

async function apiRedeem(key: string, firstName: string, lastName: string, phone: string, webhook: string) {
  const res = await fetch('/api/redeem', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, first_name: firstName, last_name: lastName, phone, webhook }),
  })
  return res.json()
}
