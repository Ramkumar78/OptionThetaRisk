import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MindsetChecklist } from './MindsetChecklist';
import React from 'react';

describe('MindsetChecklist', () => {
  it('does not render when closed', () => {
    render(
      <MindsetChecklist
        isOpen={false}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.queryByText(/Mindset Check/i)).toBeNull();
  });

  it('renders when open', () => {
    render(
      <MindsetChecklist
        isOpen={true}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText(/Mindset Check/i)).toBeInTheDocument();
  });

  it('calls onClose when Cancel is clicked', () => {
    const handleClose = vi.fn();
    render(
      <MindsetChecklist
        isOpen={true}
        onConfirm={vi.fn()}
        onClose={handleClose}
      />
    );
    fireEvent.click(screen.getByText('Cancel'));
    expect(handleClose).toHaveBeenCalled();
  });

  it('disables Proceed button initially', () => {
    render(
      <MindsetChecklist
        isOpen={true}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />
    );
    const proceedBtn = screen.getByText('Proceed');
    expect(proceedBtn).toBeDisabled();
  });

  it('enables Proceed button only when correct answers are selected', () => {
    render(
        <MindsetChecklist
          isOpen={true}
          onConfirm={vi.fn()}
          onClose={vi.fn()}
        />
      );

      const proceedBtn = screen.getByText('Proceed');

      // Select incorrect answer for Q1
      const q1Yes = screen.getAllByText('Yes')[0]; // assuming order
      fireEvent.click(q1Yes);
      expect(proceedBtn).toBeDisabled();

      // Select correct answer for Q1: No
      const q1No = screen.getAllByText('No')[0];
      fireEvent.click(q1No);
      expect(proceedBtn).toBeDisabled();

      // Select correct answer for Q2: Yes
      const q2Yes = screen.getAllByText('Yes')[1];
      fireEvent.click(q2Yes);
      expect(proceedBtn).toBeDisabled();

      // Select correct answer for Q3: Yes
      const q3Yes = screen.getAllByText('Yes')[2];
      fireEvent.click(q3Yes);

      // Should be enabled now
      expect(proceedBtn).not.toBeDisabled();
  });

  it('calls onConfirm when Proceed is clicked', () => {
      const handleConfirm = vi.fn();
      render(
        <MindsetChecklist
          isOpen={true}
          onConfirm={handleConfirm}
          onClose={vi.fn()}
        />
      );

      // Answer correctly
      const q1No = screen.getAllByText('No')[0];
      const q2Yes = screen.getAllByText('Yes')[1];
      const q3Yes = screen.getAllByText('Yes')[2];

      fireEvent.click(q1No);
      fireEvent.click(q2Yes);
      fireEvent.click(q3Yes);

      fireEvent.click(screen.getByText('Proceed'));
      expect(handleConfirm).toHaveBeenCalled();
  });
});
