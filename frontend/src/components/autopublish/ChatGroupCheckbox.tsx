import { useRef, useEffect } from 'react'
import type { BotChatListItem } from '../../types/models'

interface ChatGroup {
  group_id: number
  name: string
  description?: string
  chat_ids: number[]
}

interface ChatGroupCheckboxProps {
  group: ChatGroup
  groupChats: BotChatListItem[]
  allSelected: boolean
  someSelected: boolean
  onToggle: () => void
}

export function ChatGroupCheckbox({
  group,
  groupChats,
  allSelected,
  someSelected,
  onToggle,
}: ChatGroupCheckboxProps): JSX.Element {
  const checkboxRef = useRef<HTMLInputElement>(null)
  
  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = someSelected && !allSelected
    }
  }, [someSelected, allSelected])
  
  return (
    <label className="chat-group-item">
      <input
        ref={checkboxRef}
        type="checkbox"
        checked={allSelected}
        onChange={onToggle}
      />
      <span>{group.name} ({groupChats.length} чатов)</span>
    </label>
  )
}

