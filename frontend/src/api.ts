export async function apiLogin(phone: string) {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  })
  return res.json()
}

export async function apiRegister(phone: string, firstName: string, lastName: string) {
  const res = await fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, first_name: firstName, last_name: lastName }),
  })
  return res.json()
}

export async function apiConfirm(phone: string) {
  const res = await fetch('/api/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  })
  return res.json()
}

export async function apiRedeem(key: string, firstName: string, lastName: string, phone: string, webhook: string) {
  const res = await fetch('/api/redeem', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, first_name: firstName, last_name: lastName, phone, webhook }),
  })
  return res.json()
}

export async function apiQuota() {
  const res = await fetch('/api/quota')
  return res.json()
}
