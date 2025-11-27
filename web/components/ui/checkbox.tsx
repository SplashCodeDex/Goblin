import * as React from "react"

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "checked"> {
  checked?: boolean | "indeterminate"
  onCheckedChange?: (checked: boolean | "indeterminate") => void
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { className = "", checked, onCheckedChange, ...props }, ref
) {
  return (
    <input
      ref={ref}
      type="checkbox"
      className={("h-4 w-4 rounded border border-white/20 bg-transparent " + className).trim()}
      checked={Boolean(checked)}
      onChange={(e) => onCheckedChange?.(e.target.checked)}
      {...props}
    />
  )
})
