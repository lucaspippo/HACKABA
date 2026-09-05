import { MessagePrimitive } from "@assistant-ui/react";

export default function UserMessage() {
  return (
    <MessagePrimitive.Root className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-line rounded-2xl rounded-tr-md bg-tinta px-3.5 py-2.5 text-[0.95rem] leading-snug text-crema">
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  );
}
