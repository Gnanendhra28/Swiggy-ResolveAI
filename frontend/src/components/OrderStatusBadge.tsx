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

  const getBadgeConfig = () => {
    switch (normalized) {
      case 'DELIVERED':
        if (isDelayed) {
          return {
            label: 'Delivered (Delayed)',
            bg: 'bg-[#FFF8E6]',
            text: 'text-[#D97706]',
            border: 'border-[#FDE68A]',
            dot: 'bg-[#D97706]',
          };
        }
        return {
          label: 'Delivered on Time',
          bg: 'bg-[#EDF7EC]',
          text: 'text-[#60B246]',
          border: 'border-[#C8E6C9]',
          dot: 'bg-[#60B246]',
        };

      case 'RECOVERED':
        return {
          label: 'Resolved with Support',
          bg: 'bg-[#EDF7EC]',
          text: 'text-[#2E7D32]',
          border: 'border-[#A5D6A7]',
          dot: 'bg-[#2E7D32]',
        };

      case 'OUT_FOR_DELIVERY':
        return {
          label: isDelayed ? 'Out for Delivery (Delayed)' : 'Out for Delivery',
          bg: isDelayed ? 'bg-[#FFF8E6]' : 'bg-[#FFF5ED]',
          text: isDelayed ? 'text-[#D97706]' : 'text-[#FC8019]',
          border: isDelayed ? 'border-[#FDE68A]' : 'border-[#FED7AA]',
          dot: isDelayed ? 'bg-[#D97706]' : 'bg-[#FC8019]',
        };

      case 'PREPARING':
      case 'READY_FOR_PICKUP':
        return {
          label: isDelayed ? 'Kitchen Delay' : 'Preparing in Kitchen',
          bg: 'bg-[#FFF8E6]',
          text: 'text-[#D97706]',
          border: 'border-[#FDE68A]',
          dot: 'bg-[#D97706]',
        };

      case 'FAILED_RECOVERY':
      case 'ESCALATED':
        return {
          label: 'Needs Attention',
          bg: 'bg-[#FDF0F1]',
          text: 'text-[#E23744]',
          border: 'border-[#FECDD3]',
          dot: 'bg-[#E23744]',
        };

      case 'CANCELLED':
        return {
          label: 'Cancelled',
          bg: 'bg-[#FDF0F1]',
          text: 'text-[#E23744]',
          border: 'border-[#FECDD3]',
          dot: 'bg-[#E23744]',
        };

      case 'PLACED':
      case 'CONFIRMED':
        return {
          label: 'Order Placed',
          bg: 'bg-[#F4F5F7]',
          text: 'text-[#686B78]',
          border: 'border-[#E2E5E8]',
          dot: 'bg-[#686B78]',
        };

      default:
        return {
          label: normalized.replace(/_/g, ' '),
          bg: 'bg-[#F4F5F7]',
          text: 'text-[#686B78]',
          border: 'border-[#E2E5E8]',
          dot: 'bg-[#686B78]',
        };
    }
  };

  const config = getBadgeConfig();

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${config.bg} ${config.text} ${config.border} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      <span>{config.label}</span>
    </span>
  );
};
