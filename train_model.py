import torch
import torch.nn as nn
import torch.optim as optim
import yfinance as yf
import numpy as np
import os

# Define the LSTM Model
class ReversalLSTM(nn.Module):
    def __init__(self, input_size=1, hidden_size=32, num_layers=1, output_size=1):
        super(ReversalLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return self.sigmoid(out)

def train_and_save():
    print("Fetching training data...")
    # List of liquid tickers for training data
    tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "TSLA", "NVDA", "AMD", "GOOGL", "AMZN"]

    all_sequences = []
    all_labels = []

    # Parameters
    seq_length = 10
    prediction_window = 5

    for ticker in tickers:
        try:
            # Download 2 years of data
            df = yf.download(ticker, period="2y", progress=False)
            if df.empty:
                continue

            closes = df['Close'].values
            if len(closes) < seq_length + prediction_window:
                continue

            # Normalize (Percent change)
            # We train on % change to be price-agnostic
            pct_changes = df['Close'].pct_change().fillna(0).values

            for i in range(seq_length, len(pct_changes) - prediction_window):
                # Input: Sequence of last 10 days % change
                seq = pct_changes[i-seq_length:i]

                # Label: 1 if price in 5 days > current price, else 0
                current_price = closes[i]
                future_price = closes[i + prediction_window]
                label = 1.0 if future_price > current_price else 0.0

                all_sequences.append(seq)
                all_labels.append(label)

        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    if not all_sequences:
        print("No training data generated.")
        return

    print(f"Training on {len(all_sequences)} samples...")

    # Convert to Tensor
    # Ensure numpy array is float32
    X_np = np.array(all_sequences, dtype=np.float32)

    if X_np.ndim == 3:
        # If already 3D (N, 10, 1), assume it's correct
        X = torch.tensor(X_np)
    elif X_np.ndim == 2:
        # If 2D (N, 10), unsqueeze to make (N, 10, 1)
        X = torch.tensor(X_np).unsqueeze(-1)
    else:
        print(f"Unexpected shape: {X_np.shape}")
        return

    y = torch.tensor(np.array(all_labels), dtype=torch.float32).unsqueeze(-1)    # (N, 1)

    print(f"Input shape: {X.shape}")

    # Train Model
    model = ReversalLSTM()
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)

    epochs = 50 # Quick training
    for epoch in range(epochs):
        outputs = model(X)
        loss = criterion(outputs, y)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if (epoch+1) % 10 == 0:
            print(f'Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}')

    # Save
    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), "models/reversal_model.pth")
    print("Model saved to models/reversal_model.pth")

if __name__ == "__main__":
    train_and_save()
