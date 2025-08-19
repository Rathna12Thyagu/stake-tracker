import asyncio
import json
import threading
import time
import logging
from typing import Optional
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import yfinance as yf
import streamlit as st
from streamlit.components.v1 import html
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app for WebSocket
fastapi_app = FastAPI(title="BELRISE Stock Tracker API")

class StockDataManager:
    def __init__(self):
        self.current_price: Optional[float] = None
        self.last_update: Optional[float] = None
        
    async def get_stock_price(self) -> Optional[float]:
        """Fetch stock price with error handling"""
        try:
            ticker = yf.Ticker("BELRISE.NS")
            data = ticker.history(period="1d")
            if not data.empty:
                price = float(data['Close'][-1])
                self.current_price = price
                self.last_update = time.time()
                return price
        except Exception as e:
            logger.error(f"Error fetching stock data: {e}")
        return None

# Global stock manager
stock_manager = StockDataManager()

@fastapi_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            price = await stock_manager.get_stock_price()
            if price is not None:
                await websocket.send_text(f"{price:.2f}")
                logger.debug(f"Sent price: {price:.2f}")
            else:
                # Send last known price if available
                if stock_manager.current_price:
                    await websocket.send_text(f"{stock_manager.current_price:.2f}")
                else:
                    await websocket.send_text("0.00")
            
            await asyncio.sleep(3)  # Reduced frequency for Railway
            
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@fastapi_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "last_price": stock_manager.current_price,
        "last_update": stock_manager.last_update
    }

def run_fastapi():
    """Run FastAPI server in a separate thread"""
    try:
        # Use Railway's internal port for WebSocket
        port = int(os.getenv("WEBSOCKET_PORT", "8501"))
        uvicorn.run(
            fastapi_app, 
            host="0.0.0.0", 
            port=port,
            log_level="info",
            access_log=False
        )
    except Exception as e:
        logger.error(f"FastAPI server error: {e}")

# Start FastAPI server in background (only once)
if 'fastapi_started' not in st.session_state:
    st.session_state.fastapi_started = True
    logger.info("Starting FastAPI server...")
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()
    time.sleep(3)  # Give server more time to start on Railway

# Streamlit app configuration
st.set_page_config(
    layout="wide", 
    page_title="BELRISE Tracker",
    page_icon="📈",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better mobile responsiveness
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
    }
    
    .stApp > header {
        background-color: transparent;
    }
    
    .stApp {
        margin-top: -80px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Real-Time BELRISE Price Tracker")

# Investment configuration
INVESTMENT_CONFIG = {
    "total_investment": 14940,
    "total_shares": 166,
    "avg_price": 90,
    "stake_holders": ['Rathna', 'Esvar', 'Hari'],
    "amounts": [7940, 3000, 4000]
}

# Calculate stake data
stake_data = [
    {
        "name": name, 
        "amount": amount, 
        "percent": round(amount * 100 / INVESTMENT_CONFIG["total_investment"], 2)
    }
    for name, amount in zip(INVESTMENT_CONFIG["stake_holders"], INVESTMENT_CONFIG["amounts"])
]

# Get WebSocket URL for Railway deployment
def get_websocket_url():
    # Railway provides these environment variables
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    railway_url = os.getenv("RAILWAY_STATIC_URL")
    
    if railway_domain:
        return f"wss://{railway_domain}/ws"
    elif railway_url:
        return f"wss://{railway_url}/ws" 
    else:
        # Fallback for local development
        return "ws://localhost:8501/ws"

ws_url = get_websocket_url()

# HTML template optimized for Railway deployment
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BELRISE Stock Tracker</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            transition: transform 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-label {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 8px;
        }}
        
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        
        th, td {{
            padding: 15px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }}
        
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
        }}
        
        tr:hover {{
            background-color: #f8f9fa;
        }}
        
        .status {{
            padding: 8px 15px;
            border-radius: 25px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .connected {{ 
            background: #10b981; 
            color: white;
        }}
        
        .disconnected {{ 
            background: #ef4444; 
            color: white;
        }}
        
        .reconnecting {{
            background: #f59e0b;
            color: white;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
                margin: 5px;
                border-radius: 10px;
            }}
            
            .header {{
                flex-direction: column;
                gap: 15px;
                text-align: center;
            }}
            
            .stats {{
                grid-template-columns: 1fr;
                gap: 15px;
            }}
            
            .stat-value {{
                font-size: 22px;
            }}
            
            table {{
                font-size: 13px;
            }}
            
            th, td {{
                padding: 8px 4px;
            }}
        }}
        
        .loading {{
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>📈 BELRISE Portfolio</h2>
            <span id="status" class="status disconnected">
                <span class="loading"></span> Connecting...
            </span>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">🏷️ Live Price</div>
                <div class="stat-value" id="price">₹0.00</div>
                <div id="price-change" style="font-size: 14px; margin-top: 5px;"></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">💰 Portfolio Value</div>
                <div class="stat-value" id="market_value">₹0.00</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📊 Total P&L</div>
                <div class="stat-value" id="profit_loss">₹0.00</div>
            </div>
        </div>

        <div class="chart-container">
            <div id="chart" style="width:100%;height:350px;"></div>
        </div>

        <h3 style="margin-bottom: 20px; color: #4a5568;">👥 Stakeholder Portfolio</h3>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Investment</th>
                    <th>Share %</th>
                    <th>Current Value</th>
                    <th>P&L</th>
                    <th>Return %</th>
                </tr>
            </thead>
            <tbody id="stake-table-body">
            </tbody>
        </table>
    </div>

    <script>
        // Configuration
        const CONFIG = {{
            totalShares: {INVESTMENT_CONFIG["total_shares"]},
            avgPrice: {INVESTMENT_CONFIG["avg_price"]},
            totalInvestment: {INVESTMENT_CONFIG["total_investment"]},
            stakeData: {json.dumps(stake_data)},
            wsUrl: "{ws_url}",
            maxDataPoints: 50,
            reconnectDelay: 5000
        }};
        
        // DOM elements
        const elements = {{
            price: document.getElementById("price"),
            priceChange: document.getElementById("price-change"),
            marketValue: document.getElementById("market_value"),
            profitLoss: document.getElementById("profit_loss"),
            status: document.getElementById("status"),
            tableBody: document.getElementById("stake-table-body")
        }};
        
        // Data storage
        let priceData = [];
        let timeData = [];
        let lastPrice = null;
        let socket = null;
        let reconnectTimer = null;
        
        // Initialize stakeholder table
        function initializeTable() {{
            CONFIG.stakeData.forEach(item => {{
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td><strong>${{item.name}}</strong></td>
                    <td>₹${{item.amount.toLocaleString()}}</td>
                    <td>${{item.percent.toFixed(1)}}%</td>
                    <td id="value-${{item.name}}">₹0.00</td>
                    <td id="profit-${{item.name}}">₹0.00</td>
                    <td id="return-${{item.name}}">0.00%</td>
                `;
                elements.tableBody.appendChild(row);
            }});
        }}
        
        // Initialize chart
        function initializeChart() {{
            const layout = {{
                title: {{
                    text: "Live Price Movement",
                    font: {{ size: 16, color: "#4a5568" }}
                }},
                xaxis: {{ 
                    title: "Time",
                    showgrid: true,
                    gridcolor: "#e2e8f0"
                }},
                yaxis: {{ 
                    title: "Price (₹)",
                    showgrid: true,
                    gridcolor: "#e2e8f0"
                }},
                showlegend: false,
                plot_bgcolor: "#f7fafc",
                paper_bgcolor: "#ffffff",
                margin: {{ t: 40, r: 20, b: 40, l: 50 }},
                responsive: true
            }};
            
            const trace = {{
                x: timeData,
                y: priceData,
                type: "scatter",
                mode: "lines+markers",
                name: "BELRISE",
                line: {{ 
                    color: "#667eea", 
                    width: 2,
                    shape: "spline"
                }},
                marker: {{ 
                    color: "#764ba2", 
                    size: 5
                }}
            }};
            
            Plotly.newPlot("chart", [trace], layout, {{responsive: true, displayModeBar: false}});
        }}
        
        // Format currency
        function formatCurrency(value) {{
            return "₹" + value.toLocaleString(undefined, {{
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }});
        }}
        
        // Update display with new price
        function updateDisplay(livePrice) {{
            const now = new Date();
            
            // Update main stats
            elements.price.textContent = formatCurrency(livePrice);
            
            // Price change indicator
            if (lastPrice !== null) {{
                const change = livePrice - lastPrice;
                const changePercent = ((change / lastPrice) * 100).toFixed(2);
                const arrow = change >= 0 ? "↗" : "↘";
                const color = change >= 0 ? "#10b981" : "#ef4444";
                
                elements.priceChange.innerHTML = `
                    <span style="color: ${{color}}">
                        ${{arrow}} ${{change >= 0 ? "+" : ""}}${{change.toFixed(2)}} (${{changePercent}}%)
                    </span>
                `;
            }}
            
            const marketValue = CONFIG.totalShares * livePrice;
            const totalProfit = marketValue - CONFIG.totalInvestment;
            
            elements.marketValue.textContent = formatCurrency(marketValue);
            elements.profitLoss.textContent = formatCurrency(totalProfit);
            elements.profitLoss.style.color = totalProfit >= 0 ? "#10b981" : "#ef4444";
            
            // Update stakeholder data
            CONFIG.stakeData.forEach(item => {{
                const individualShares = (item.percent * CONFIG.totalShares) / 100;
                const currentValue = livePrice * individualShares;
                const individualProfit = currentValue - item.amount;
                const returnPercent = ((individualProfit / item.amount) * 100).toFixed(2);
                
                const valueEl = document.getElementById(`value-${{item.name}}`);
                const profitEl = document.getElementById(`profit-${{item.name}}`);
                const returnEl = document.getElementById(`return-${{item.name}}`);
                
                if (valueEl && profitEl && returnEl) {{
                    valueEl.textContent = formatCurrency(currentValue);
                    profitEl.textContent = formatCurrency(individualProfit);
                    profitEl.style.color = individualProfit >= 0 ? "#10b981" : "#ef4444";
                    profitEl.style.fontWeight = "bold";
                    
                    returnEl.textContent = `${{individualProfit >= 0 ? "+" : ""}}${{returnPercent}}%`;
                    returnEl.style.color = individualProfit >= 0 ? "#10b981" : "#ef4444";
                    returnEl.style.fontWeight = "bold";
                }}
            }});
            
            // Update chart
            priceData.push(livePrice);
            timeData.push(now.toLocaleTimeString());
            
            if (priceData.length > CONFIG.maxDataPoints) {{
                priceData.shift();
                timeData.shift();
            }}
            
            Plotly.update("chart", {{
                x: [timeData],
                y: [priceData]
            }});
            
            lastPrice = livePrice;
        }}
        
        // WebSocket connection management
        function connectWebSocket() {{
            try {{
                console.log("Connecting to:", CONFIG.wsUrl);
                socket = new WebSocket(CONFIG.wsUrl);
                
                socket.onopen = function() {{
                    console.log("WebSocket connected");
                    elements.status.innerHTML = "🟢 Connected";
                    elements.status.className = "status connected";
                    
                    if (reconnectTimer) {{
                        clearTimeout(reconnectTimer);
                        reconnectTimer = null;
                    }}
                }};
                
                socket.onmessage = function(event) {{
                    const livePrice = parseFloat(event.data);
                    if (!isNaN(livePrice) && livePrice > 0) {{
                        updateDisplay(livePrice);
                    }}
                }};
                
                socket.onclose = function(event) {{
                    console.log("WebSocket closed", event);
                    elements.status.innerHTML = "🔴 Disconnected";
                    elements.status.className = "status disconnected";
                    
                    // Attempt to reconnect
                    if (!reconnectTimer) {{
                        elements.status.innerHTML = "🟡 Reconnecting...";
                        elements.status.className = "status reconnecting";
                        reconnectTimer = setTimeout(connectWebSocket, CONFIG.reconnectDelay);
                    }}
                }};
                
                socket.onerror = function(error) {{
                    console.error("WebSocket error:", error);
                    elements.status.innerHTML = "🔴 Connection Error";
                    elements.status.className = "status disconnected";
                }};
                
            }} catch (error) {{
                console.error("Failed to create WebSocket:", error);
                elements.status.innerHTML = "🔴 Connection Failed";
                elements.status.className = "status disconnected";
                
                // Try to reconnect
                if (!reconnectTimer) {{
                    reconnectTimer = setTimeout(connectWebSocket, CONFIG.reconnectDelay);
                }}
            }}
        }}
        
        // Initialize application
        function init() {{
            initializeTable();
            initializeChart();
            
            // Delay WebSocket connection to ensure backend is ready
            setTimeout(connectWebSocket, 2000);
        }}
        
        // Start the application
        document.addEventListener("DOMContentLoaded", init);
        
        // Handle page visibility changes
        document.addEventListener("visibilitychange", function() {{
            if (document.visibilityState === "visible" && (!socket || socket.readyState === WebSocket.CLOSED)) {{
                setTimeout(connectWebSocket, 1000);
            }}
        }});
    </script>
</body>
</html>
"""

# Display the application
html(html_code, height=900)