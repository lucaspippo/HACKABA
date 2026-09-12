import { useEffect, useState } from "react";
import { plainText } from "./plainText";

type Props = {
  text: string;
  isRunning: boolean;
  label: string;
};


export default function ReplyAnnouncer({ text, isRunning, label }: Props) {
  const [announcement, setAnnouncement] = useState("");

  useEffect(() => {
    if (isRunning) return;
    const spoken = plainText(text);
    setAnnouncement(spoken ? `${label} ${spoken}` : "");
  }, [isRunning, text, label]);

  return (
    <span role="status" className="sr-only">
      {announcement}
    </span>
  );
}
