import React, { type ReactNode } from 'react';

interface TooltipProps {
  content: string;
  children: ReactNode;
}

const Tooltip: React.FC<TooltipProps> = ({ content, children }) => {
  return (
    <div className="group relative inline-flex flex-col items-center">
      {children}
      <div className="pointer-events-none absolute bottom-full mb-2 w-max max-w-[200px] rounded bg-gray-900 p-2 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100 z-50 shadow-lg text-center whitespace-normal break-words">
        {content}
        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
      </div>
    </div>
  );
};

export default Tooltip;
