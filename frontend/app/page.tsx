'use client'
import { useState } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch('http://localhost:8000/api/v1/chat/exec_func_coach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'dev_user',
          message: input
        })
      })

      const data = await response.json()

      const assistantMessage: Message = { role: 'assistant', content: data.response }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, there was an error processing your request.'
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4">
      <header className="mb-4">
        <h1 className="text-2xl font-bold">Executive Function Coach</h1>
        <p className="text-gray-600">Phase 1: Testing OpenMemory integration</p>
      </header>

      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`p-3 rounded ${
            msg.role === 'user' ? 'bg-blue-100 ml-auto' : 'bg-gray-100'
          } max-w-[80%]`}>
            <div className="font-semibold text-sm mb-1">
              {msg.role === 'user' ? 'You' : 'Coach'}
            </div>
            <div>{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="bg-gray-100 p-3 rounded max-w-[80%]">
            <div className="font-semibold text-sm mb-1">Coach</div>
            <div className="text-gray-500">Thinking...</div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          className="flex-1 p-2 border rounded"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-400"
        >
          Send
        </button>
      </form>
    </div>
  )
}
