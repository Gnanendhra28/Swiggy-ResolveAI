import React from 'react';

interface OrderStatusBadgeProps {
  status: string;
  isDelayed?: boolean;
  className?: string;
}

export const OrderStatusBadge: React.FC<OrderStatusBadgeProps> = ({
  status,
  isDelayed,
  className = '',
}) => {
  const normalized = (status || '').toUpperCase();

  const getBadgeStyle = () => {
    switch (normalized) {
      case 'DELIVERED':
        if (isDelayed) {
          return {
            bg: 'bg-[#FFF8E6]',
            text: 'text-[#D97706]',
            border: 'border-[#FDE68A]',
            dot: 'bg-[#D97706]',
          };
        }
        return {
          bg: 'bg-[#EDF7EC]',
          text: 'text-[#60B246]',
          border: 'border-[#C8E6C9]',
          dot: 'bg-[#60B246]',
        };

      case 'RECOVERED':
        return {
          bg: 'bg-[#EDF7EC]',
          text: 'text-[#2E7D32]',
          border: 'border-[#A5D6A7]',
          dot: 'bg-[#2E7D32]',
        };

      case 'OUT_FOR_DELIVERY':
        return {
          bg: 'bg-[#FFF5ED]',
          text: 'text-[#FC8019]',
          border: 'border-[#FED7AA]',
          dot: 'bg-[#FC8019]',
        };

      case 'PREPARING':
      case 'READY_FOR_PICKUP':
        return {
          bg: 'bg-[#FFF8E6]',
          text: 'text-[#D97706]',
          border: 'border-[#FDE68A]',
          dot: 'bg-[#D97706]',
        };

      case 'FAILED_RECOVERY':
      case 'ESCALATED':
      case 'CANCELLED':
        return {
          bg: 'bg-[#FDF0F1]',
          text: 'text-[#E23744]',
          border: 'border-[#FECDD3]',
          dot: 'bg-[#E23744]',
        };

      case 'PLACED':
      case 'CONFIRMED':
      default:
        return {
          bg: 'bg-[#F4F5F7]',
          text: 'text-[#686B78]',
          border: 'border-[#E2E5E8]',
          dot: 'bg-[#686B78]',
        };
    }
  };

  const style = getBadgeStyle();

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${style.bg} ${style.text} ${style.border} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
      <span>{normalized.replace(/_/g, ' ')}</span>
      {isDelayed && normalized === 'DELIVERED' && (
        <span className="text-[10px] uppercase font-bold text-[#D97706] tracking-wide ml-0.5">
          (Delayed)
        </span>
      )}
    </span>
  );
};
