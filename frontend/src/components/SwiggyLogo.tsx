import React from 'react';

interface SwiggyLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showSubtitle?: boolean;
}

export const SwiggyLogo: React.FC<SwiggyLogoProps> = ({
  className = '',
  size = 'md',
  showSubtitle = true,
}) => {
  const iconSize = size === 'sm' ? 'w-7 h-7' : size === 'lg' ? 'w-11 h-11' : 'w-9 h-9';
  const titleSize = size === 'sm' ? 'text-base' : size === 'lg' ? 'text-xl' : 'text-lg';

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {/* Swiggy Iconic Orange Mark */}
      <div
        className={`${iconSize} rounded-xl bg-[#FC8019] flex items-center justify-center shadow-md shadow-orange-500/20 flex-shrink-0`}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-5 h-5 text-white"
        >
          {/* Swiggy-style delivery pin & speed wave */}
          <path
            d="M12 2C8.13 2 5 5.13 5 9C5 13.5 12 22 12 22C12 22 19 13.5 19 9C19 5.13 15.87 2 12 2ZM12 11.5C10.62 11.5 9.5 10.38 9.5 9C9.5 7.62 10.62 6.5 12 6.5C13.38 6.5 14.5 7.62 14.5 9C14.5 10.38 13.38 11.5 12 11.5Z"
            fill="currentColor"
          />
        </svg>
      </div>

      <div className="flex flex-col">
        <div className={`font-extrabold ${titleSize} tracking-tight leading-none text-[#282C3F]`}>
          Swiggy <span className="text-[#FC8019]">ResolveAI</span>
        </div>
        {showSubtitle && (
          <span className="text-[10px] text-[#686B78] font-semibold tracking-wider uppercase mt-1">
            Order Intelligence
          </span>
        )}
      </div>
    </div>
  );
};
