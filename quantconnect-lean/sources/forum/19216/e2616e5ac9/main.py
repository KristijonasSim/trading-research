from AlgorithmImports import *

class QQQSPYMomentumRotationSystem(QCAlgorithm):
    def initialize(self):
        # Backtest period
        self.set_start_date(2010, 1, 1)
        self.set_end_date(2025, 1, 1)
        self.set_cash(10000)
        
        # Add securities
        self.qqq = self.add_equity("QQQ", Resolution.DAILY).symbol
        self.spy = self.add_equity("SPY", Resolution.DAILY).symbol
        
        # Set QQQ as primary benchmark for QuantConnect comparison
        self.set_benchmark(self.qqq)
        
        # === BENCHMARK TRACKING FOR MANUAL COMPARISON ===
        self.initial_cash = 10000
        self.qqq_shares = 0
        self.spy_shares = 0
        self.qqq_benchmark_value = 10000
        self.spy_benchmark_value = 10000
        self.benchmark_initialized = False
        
        # === STRATEGY PARAMETERS ===
        self.momentum_period = 20        # 20-day momentum lookback
        self.qqq_bias = 0.01            # 1% bias toward QQQ
        self.rebalance_frequency = 5     # Rebalance every 5 days
        self.min_momentum_diff = 0.005   # 0.5% minimum difference to switch
        
        # === TRACKING VARIABLES ===
        self.current_holding = None      # Current position ("QQQ" or "SPY")
        self.last_target = None          # Last target symbol for persistence filter
        self.qqq_periods = 0            # Count of periods holding QQQ
        self.spy_periods = 0            # Count of periods holding SPY
        self.total_switches = 0         # Total number of switches
        self.last_rebalance_date = None # Track last rebalance date
        
        # === PERFORMANCE TRACKING ===
        self.trade_log = []             # Store trade history
        
        # Schedule rebalancing
        self.schedule.on(
            self.date_rules.every(DayOfWeek.MONDAY),
            self.time_rules.after_market_open(self.qqq, 30),
            self.rebalance
        )
        
        # Daily performance logging - changed to monthly for cleaner output
        self.schedule.on(
            self.date_rules.month_start(),
            self.time_rules.after_market_open(self.qqq, 30),
            self.log_performance
        )
        
        self.log("=== QQQ/SPY MOMENTUM ROTATION SYSTEM INITIALIZED ===")
        self.log(f"Momentum Period: {self.momentum_period} days")
        self.log(f"QQQ Bias: {self.qqq_bias:.1%}")
        self.log(f"Min Momentum Diff: {self.min_momentum_diff:.1%}")

    def rebalance(self):
        """Main rebalancing logic with comprehensive error handling"""
        if self.is_warming_up:
            return
            
        # Skip if we just rebalanced recently
        if (self.last_rebalance_date is not None and 
            (self.time.date() - self.last_rebalance_date).days < self.rebalance_frequency):
            return
        
        try:
            self.log(f"=== QQQ-PRIMARY REBALANCE: {self.time.strftime('%Y-%m-%d')} ===")
            
            # === STEP 1: GET MOMENTUM DATA WITH ERROR HANDLING ===
            qqq_momentum, spy_momentum = self.get_momentum_data()
            if qqq_momentum is None or spy_momentum is None:
                self.log("ERROR: Could not calculate momentum - skipping rebalance")
                return
            
            # === STEP 2: CALCULATE SCORES ===
            qqq_score = qqq_momentum + self.qqq_bias
            spy_score = spy_momentum
            score_diff = qqq_score - spy_score
            
            self.log(f"QQQ Momentum: {qqq_momentum:.2%}, SPY Momentum: {spy_momentum:.2%}")
            self.log(f"QQQ Score: {qqq_score:.2%}, SPY Score: {spy_score:.2%}")
            self.log(f"Score Difference: {score_diff:.2%}")
            
            # === STEP 3: DETERMINE TARGET ===
            if score_diff > self.min_momentum_diff:
                target_symbol = self.qqq
                target_name = "QQQ"
                allocation = 1.0
            elif score_diff < -self.min_momentum_diff:
                target_symbol = self.spy
                target_name = "SPY"
                allocation = 1.0
            else:
                # Scores too close - maintain current position or default to QQQ
                if self.current_holding:
                    self.log(f"MOMENTUM INDECISIVE: Maintaining {self.current_holding}")
                    return
                else:
                    target_symbol = self.qqq
                    target_name = "QQQ"
                    allocation = 1.0
                    self.log("MOMENTUM INDECISIVE: Defaulting to QQQ")
            
            # === STEP 4: PERSISTENCE FILTER ===
            if self.last_target == target_symbol:
                self.log(f"PERSISTENCE FILTER: Holding {target_name} - consistent momentum")
                return
            
            # Update last target after persistence check
            self.last_target = target_symbol
            
            # === STEP 5: CHECK IF ALREADY IN POSITION ===
            if self.current_holding == target_name:
                self.log(f"ALREADY HOLDING: {target_name} at {allocation:.0%} allocation")
                return
            
            # === STEP 6: EXECUTE TRADE ===
            success = self.execute_rotation(target_symbol, target_name, allocation)
            
            if success:
                # Only increment counters after successful trade
                if target_name == "QQQ":
                    self.qqq_periods += 1
                else:
                    self.spy_periods += 1
                
                self.last_rebalance_date = self.time.date()
                
        except Exception as e:
            self.log(f"REBALANCE ERROR: {str(e)}")
            self.debug(f"Rebalance exception: {e}")

    def get_momentum_data(self):
        """Safely retrieve and calculate momentum data"""
        try:
            # Get QQQ history
            try:
                qqq_hist = self.history(self.qqq, self.momentum_period + 1, Resolution.DAILY)
                if qqq_hist.empty or len(qqq_hist) < self.momentum_period + 1:
                    self.log("ERROR: Insufficient QQQ history")
                    return None, None
                qqq_closes = qqq_hist['close']
            except Exception as e:
                self.log(f"ERROR: QQQ history retrieval failed: {str(e)}")
                return None, None
            
            # Get SPY history
            try:
                spy_hist = self.history(self.spy, self.momentum_period + 1, Resolution.DAILY)
                if spy_hist.empty or len(spy_hist) < self.momentum_period + 1:
                    self.log("ERROR: Insufficient SPY history")
                    return None, None
                spy_closes = spy_hist['close']
            except Exception as e:
                self.log(f"ERROR: SPY history retrieval failed: {str(e)}")
                return None, None
            
            # Calculate momentum safely
            try:
                qqq_momentum = (qqq_closes.iloc[-1] - qqq_closes.iloc[0]) / qqq_closes.iloc[0]
                spy_momentum = (spy_closes.iloc[-1] - spy_closes.iloc[0]) / spy_closes.iloc[0]
                return qqq_momentum, spy_momentum
            except Exception as e:
                self.log(f"ERROR: Momentum calculation failed: {str(e)}")
                return None, None
                
        except Exception as e:
            self.log(f"ERROR: get_momentum_data failed: {str(e)}")
            return None, None

    def execute_rotation(self, target_symbol, target_name, allocation):
        """Execute the rotation trade with error handling"""
        try:
            # Liquidate current positions
            self.liquidate()
            
            # Calculate position size
            quantity = self.calculate_order_quantity(target_symbol, allocation)
            
            if quantity == 0:
                self.log(f"ERROR: Cannot calculate valid quantity for {target_name}")
                return False
            
            # Execute trade
            order_ticket = self.market_order(target_symbol, quantity)
            
            if order_ticket:
                # Update tracking
                self.current_holding = target_name
                self.total_switches += 1
                
                # Log trade
                self.log("=== ROTATION EXECUTED ===")
                self.log(f"NEW POSITION: {target_name} | Allocation: {allocation:.0%} | Shares: {quantity}")
                self.log(f"Total Switches: {self.total_switches}")
                
                # Store trade record
                self.trade_log.append({
                    'date': self.time,
                    'action': 'BUY',
                    'symbol': target_name,
                    'quantity': quantity,
                    'price': self.securities[target_symbol].price,
                    'allocation': allocation
                })
                
                return True
            else:
                self.log(f"ERROR: Order failed for {target_name}")
                return False
                
        except Exception as e:
            self.log(f"ERROR: execute_rotation failed: {str(e)}")
            return False

    def log_performance(self):
        """Log monthly performance summary with benchmark comparison"""
        try:
            # Initialize benchmarks on first run
            if not self.benchmark_initialized and self.securities[self.qqq].price > 0:
                qqq_price = self.securities[self.qqq].price
                spy_price = self.securities[self.spy].price
                
                self.qqq_shares = self.initial_cash / qqq_price
                self.spy_shares = self.initial_cash / spy_price
                self.benchmark_initialized = True
                self.log(f"BENCHMARKS INITIALIZED: QQQ shares: {self.qqq_shares:.2f}, SPY shares: {self.spy_shares:.2f}")
            
            # Calculate current values
            portfolio_value = self.portfolio.total_portfolio_value
            cash = self.portfolio.cash
            invested = portfolio_value - cash
            
            # Calculate benchmark values
            if self.benchmark_initialized:
                qqq_price = self.securities[self.qqq].price
                spy_price = self.securities[self.spy].price
                
                self.qqq_benchmark_value = self.qqq_shares * qqq_price
                self.spy_benchmark_value = self.spy_shares * spy_price
                
                # Calculate returns
                strategy_return = (portfolio_value - self.initial_cash) / self.initial_cash
                qqq_return = (self.qqq_benchmark_value - self.initial_cash) / self.initial_cash
                spy_return = (self.spy_benchmark_value - self.initial_cash) / self.initial_cash
                
                self.log(f"=== MONTHLY PERFORMANCE: {self.time.strftime('%Y-%m-%d')} ===")
                self.log(f"STRATEGY VALUE: ${portfolio_value:,.2f} | Return: {strategy_return:.2%}")
                self.log(f"QQQ B&H VALUE: ${self.qqq_benchmark_value:,.2f} | Return: {qqq_return:.2%}")
                self.log(f"SPY B&H VALUE: ${self.spy_benchmark_value:,.2f} | Return: {spy_return:.2%}")
                
                # Performance vs benchmarks
                vs_qqq = strategy_return - qqq_return
                vs_spy = strategy_return - spy_return
                self.log(f"OUTPERFORMANCE: vs QQQ: {vs_qqq:.2%} | vs SPY: {vs_spy:.2%}")
                
                # Plot benchmark comparison for charts
                self.plot("Benchmark Comparison", "Strategy", portfolio_value)
                self.plot("Benchmark Comparison", "QQQ B&H", self.qqq_benchmark_value)
                self.plot("Benchmark Comparison", "SPY B&H", self.spy_benchmark_value)
                
            else:
                self.log(f"=== MONTHLY PERFORMANCE: {self.time.strftime('%Y-%m-%d')} ===")
                self.log(f"Portfolio Value: ${portfolio_value:,.2f}")
            
            if self.current_holding:
                self.log(f"Current Position: {self.current_holding}")
            
            self.log(f"QQQ Periods: {self.qqq_periods} | SPY Periods: {self.spy_periods}")
            self.log(f"Total Switches: {self.total_switches}")
            
        except Exception as e:
            self.log(f"ERROR: log_performance failed: {str(e)}")

    def on_order_event(self, order_event):
        """Track order execution"""
        if order_event.status == OrderStatus.FILLED:
            self.log(f"ORDER FILLED: {order_event.symbol} - {order_event.fill_quantity} shares @ ${order_event.fill_price:.2f}")

    def on_end_of_algorithm(self):
        """Final performance summary with detailed benchmark comparison"""
        try:
            final_value = self.portfolio.total_portfolio_value
            initial_value = self.initial_cash
            
            # Calculate final benchmark values
            if self.benchmark_initialized:
                qqq_final_price = self.securities[self.qqq].price
                spy_final_price = self.securities[self.spy].price
                
                qqq_final_value = self.qqq_shares * qqq_final_price
                spy_final_value = self.spy_shares * spy_final_price
                
                # Calculate total returns
                strategy_total_return = (final_value - initial_value) / initial_value
                qqq_total_return = (qqq_final_value - initial_value) / initial_value
                spy_total_return = (spy_final_value - initial_value) / initial_value
                
                # Calculate annualized returns (15 years: 2010-2025)
                years = 15
                strategy_annual = (final_value / initial_value) ** (1/years) - 1
                qqq_annual = (qqq_final_value / initial_value) ** (1/years) - 1
                spy_annual = (spy_final_value / initial_value) ** (1/years) - 1
                
                self.log("=" * 60)
                self.log("=== FINAL PERFORMANCE COMPARISON (2010-2025) ===")
                self.log("=" * 60)
                
                self.log(f"INITIAL INVESTMENT: ${initial_value:,.2f}")
                self.log("")
                
                self.log("FINAL VALUES:")
                self.log(f"  Strategy (Rotation): ${final_value:,.2f}")
                self.log(f"  QQQ Buy & Hold:     ${qqq_final_value:,.2f}")
                self.log(f"  SPY Buy & Hold:     ${spy_final_value:,.2f}")
                self.log("")
                
                self.log("TOTAL RETURNS:")
                self.log(f"  Strategy: {strategy_total_return:.2%}")
                self.log(f"  QQQ B&H:  {qqq_total_return:.2%}")
                self.log(f"  SPY B&H:  {spy_total_return:.2%}")
                self.log("")
                
                self.log("ANNUALIZED RETURNS:")
                self.log(f"  Strategy: {strategy_annual:.2%}")
                self.log(f"  QQQ B&H:  {qqq_annual:.2%}")
                self.log(f"  SPY B&H:  {spy_annual:.2%}")
                self.log("")
                
                self.log("OUTPERFORMANCE:")
                self.log(f"  vs QQQ: {strategy_total_return - qqq_total_return:+.2%} total | {strategy_annual - qqq_annual:+.2%} annual")
                self.log(f"  vs SPY: {strategy_total_return - spy_total_return:+.2%} total | {strategy_annual - spy_annual:+.2%} annual")
                self.log("")
                
                # Strategy statistics
                self.log("STRATEGY STATISTICS:")
                self.log(f"  Total Switches: {self.total_switches}")
                self.log(f"  QQQ Periods: {self.qqq_periods}")
                self.log(f"  SPY Periods: {self.spy_periods}")
                
                if self.total_switches > 0:
                    avg_hold_period = (self.qqq_periods + self.spy_periods) / self.total_switches
                    self.log(f"  Avg Hold Period: {avg_hold_period:.1f} rebalances")
                
                if self.current_holding:
                    self.log(f"  Final Position: {self.current_holding}")
                
                self.log("=" * 60)
                
                # Determine winner
                if strategy_total_return > qqq_total_return and strategy_total_return > spy_total_return:
                    self.log("*** STRATEGY WINS! Rotation outperformed both benchmarks! ***")
                elif strategy_total_return > max(qqq_total_return, spy_total_return):
                    best_benchmark = "QQQ" if qqq_total_return > spy_total_return else "SPY"
                    self.log(f"Strategy beat {best_benchmark} but not the better benchmark")
                else:
                    self.log("Strategy underperformed both benchmarks")
                
            else:
                # Fallback if benchmarks weren't initialized
                strategy_total_return = (final_value - initial_value) / initial_value
                strategy_annual = (final_value / initial_value) ** (1/15) - 1
                
                self.log("=== FINAL ALGORITHM SUMMARY ===")
                self.log(f"Initial Value: ${initial_value:,.2f}")
                self.log(f"Final Value: ${final_value:,.2f}")
                self.log(f"Total Return: {strategy_total_return:.2%}")
                self.log(f"Annualized Return: {strategy_annual:.2%}")
                self.log(f"Total Switches: {self.total_switches}")
                
        except Exception as e:
            self.log(f"ERROR: on_end_of_algorithm failed: {str(e)}")
            