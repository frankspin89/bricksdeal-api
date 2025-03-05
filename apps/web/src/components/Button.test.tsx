import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';

describe('Button Component', () => {
  it('renders correctly with default props', () => {
    render(<Button>Click me</Button>);
    
    const button = screen.getByTestId('button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Click me');
    expect(button).toHaveAttribute('type', 'button');
    expect(button).not.toBeDisabled();
  });
  
  it('applies the correct variant classes', () => {
    const { rerender } = render(<Button variant="primary">Primary</Button>);
    let button = screen.getByTestId('button');
    expect(button.className).toContain('bg-blue-600');
    
    rerender(<Button variant="secondary">Secondary</Button>);
    button = screen.getByTestId('button');
    expect(button.className).toContain('bg-gray-200');
    
    rerender(<Button variant="outline">Outline</Button>);
    button = screen.getByTestId('button');
    expect(button.className).toContain('border-gray-300');
  });
  
  it('applies the correct size classes', () => {
    const { rerender } = render(<Button size="sm">Small</Button>);
    let button = screen.getByTestId('button');
    expect(button.className).toContain('px-3 py-1.5 text-sm');
    
    rerender(<Button size="md">Medium</Button>);
    button = screen.getByTestId('button');
    expect(button.className).toContain('px-4 py-2 text-base');
    
    rerender(<Button size="lg">Large</Button>);
    button = screen.getByTestId('button');
    expect(button.className).toContain('px-6 py-3 text-lg');
  });
  
  it('handles disabled state correctly', () => {
    render(<Button disabled>Disabled</Button>);
    const button = screen.getByTestId('button');
    expect(button).toBeDisabled();
    expect(button.className).toContain('opacity-50');
    expect(button.className).toContain('cursor-not-allowed');
  });
  
  it('calls onClick handler when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    const button = screen.getByTestId('button');
    fireEvent.click(button);
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
  
  it('does not call onClick when disabled', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick} disabled>Click me</Button>);
    
    const button = screen.getByTestId('button');
    fireEvent.click(button);
    
    expect(handleClick).not.toHaveBeenCalled();
  });
  
  it('applies custom className correctly', () => {
    render(<Button className="custom-class">Custom</Button>);
    const button = screen.getByTestId('button');
    expect(button.className).toContain('custom-class');
  });
}); 