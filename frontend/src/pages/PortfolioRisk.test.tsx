import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import PortfolioRisk from './PortfolioRisk';

// Mock axios
vi.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock Chart.js to avoid canvas errors in test environment
vi.mock('react-chartjs-2', () => ({
    Doughnut: () => <div data-testid="doughnut-chart">Doughnut Chart</div>,
}));

describe('PortfolioRisk Component', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('renders the component correctly', () => {
        render(<PortfolioRisk />);
        expect(screen.getByText('Portfolio Risk Heatmap')).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/NVDA, 5000/)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Analyze Risk/i })).toBeInTheDocument();
    });

    it('validates empty input', async () => {
        render(<PortfolioRisk />);
        const button = screen.getByRole('button', { name: /Analyze Risk/i });

        fireEvent.click(button);

        await waitFor(() => {
            expect(screen.getByText(/No valid positions/)).toBeInTheDocument();
        });
    });

    it('handles API success and displays report', async () => {
        const mockReport = {
            total_value: 10000,
            diversification_score: 75,
            concentration_warnings: ['Too much NVDA'],
            sector_warnings: ['Tech Overload'],
            sector_breakdown: [{ name: 'Tech', value: 60 }, { name: 'Cash', value: 40 }],
            high_correlation_pairs: [{ pair: 'NVDA+AMD', score: 0.9, verdict: '🔥 DUPLICATE RISK' }],
            correlation_matrix: {
                "NVDA": {"NVDA": 1.0, "AMD": 0.9},
                "AMD": {"NVDA": 0.9, "AMD": 1.0}
            }
        };

        mockedAxios.post.mockResolvedValueOnce({ data: mockReport });

        render(<PortfolioRisk />);
        const input = screen.getByPlaceholderText(/NVDA, 5000/);
        const button = screen.getByRole('button', { name: /Analyze Risk/i });

        await userEvent.type(input, 'NVDA, 10000');
        fireEvent.click(button);

        // Check Loading State (optional, might be too fast)
        // expect(screen.getByText(/Analyzing.../)).toBeInTheDocument();

        await waitFor(() => {
            expect(screen.getByText('75')).toBeInTheDocument(); // Score
            expect(screen.getByText('✅ Well Diversified')).toBeInTheDocument();
            expect(screen.getByText('Too much NVDA')).toBeInTheDocument();
            expect(screen.getByText('Tech Overload')).toBeInTheDocument();
            expect(screen.getByText('NVDA+AMD')).toBeInTheDocument();

            // Heatmap Checks
            expect(screen.getByText('Correlation Matrix')).toBeInTheDocument();
            expect(screen.getAllByText('0.9').length).toBeGreaterThanOrEqual(2); // Matrix cells
            expect(screen.getAllByText('1.0').length).toBeGreaterThanOrEqual(2); // Diagonals
        });
    });

    it('handles API error', async () => {
        mockedAxios.post.mockRejectedValueOnce({
            response: { data: { error: 'Backend explosion' } }
        });

        render(<PortfolioRisk />);
        const input = screen.getByPlaceholderText(/NVDA, 5000/);
        const button = screen.getByRole('button', { name: /Analyze Risk/i });

        await userEvent.type(input, 'NVDA, 10000');
        fireEvent.click(button);

        await waitFor(() => {
            expect(screen.getByText('Backend explosion')).toBeInTheDocument();
        });
    });
});
