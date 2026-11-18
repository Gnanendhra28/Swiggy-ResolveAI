import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'default';
  trend?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = 'default',
  trend,
}) => {
  const getStyles = () => {
    switch (variant) {
      case 'primary':
        return {
          iconBg: 'bg-[#FFF5ED] text-[#FC8019]',
          valueColor: 'text-[#FC8019]',
          badgeBg: 'bg-[#FFF5ED] text-[#FC8019]',
        };
      case 'success':
        return {
          iconBg: 'bg-[#EDF7EC] text-[#60B246]',
          valueColor: 'text-[#60B246]',
          badgeBg: 'bg-[#EDF7EC] text-[#60B246]',
        };
      case 'danger':
        return {
          iconBg: 'bg-[#FDF0F1] text-[#E23744]',
          valueColor: 'text-[#E23744]',
          badgeBg: 'bg-[#FDF0F1] text-[#E23744]',
        };
      case 'warning':
        return {
          iconBg: 'bg-[#FFF8E6] text-[#D97706]',
          valueColor: 'text-[#D97706]',
          badgeBg: 'bg-[#FFF8E6] text-[#D97706]',
        };
      case 'default':
      default:
        return {
          iconBg: 'bg-[#F4F5F7] text-[#282C3F]',
          valueColor: 'text-[#282C3F]',
          badgeBg: 'bg-[#F4F5F7] text-[#686B78]',
        };
    }
  };

  const styles = getStyles();

  return (
    <div className="bg-white rounded-2xl border border-[#E9ECEE] p-5 shadow-[0_2px_8px_rgba(40,44,63,0.06)] hover:shadow-[0_4px_16px_rgba(40,44,63,0.1)] transition-all flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-[#686B78] uppercase tracking-wider">
          {title}
        </span>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${styles.iconBg}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="mt-4">
        <div className={`text-3xl font-extrabold tracking-tight ${styles.valueColor}`}>
          {value}
        </div>
        {subtitle && (
          <p className="text-xs text-[#93959F] mt-1 font-medium flex items-center gap-1.5">
            {subtitle}
          </p>
        )}
      </div>

      {trend && (
        <div className="mt-3 pt-3 border-t border-[#F4F5F7] text-[11px] font-medium text-[#686B78]">
          {trend}
        </div>
      )}
    </div>
  );
};
