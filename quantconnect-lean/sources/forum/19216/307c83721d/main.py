# QQQ-PRIMARY STRATEGY - MINIMAL ROTATION FOR MAXIMUM QQQ EXPOSURE
# Major fixes: Strong QQQ bias, eliminate SHY, reduce rotation frequency
# Author:Bob Claude AI and ChatGPT - QQQ-OPTIMIZED FOR BULL RUN CAPTURE

from AlgorithmImports import *
from datetime import timedelta

class QQQPrimaryStrategy(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2010, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(10000)

        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE, AccountType.CASH)
        self.set_warm_up(timedelta(days=30))

        self.qqq = self.add_equity("QQQ", Resolution.DAILY).symbol
        self.spy = self.add_equity("SPY", Resolution.DAILY).symbol
        # REMOVED: SHY bonds - eliminate defensive drag

        # AGGRESSIVE QQQ-FAVORING PARAMETERS
        self.momentum_period = 20
        self.momentum_threshold = 0.015  # Increased from 0.005 - only rotate for significant differences
        self.qqq_severe_weakness = -0.15  # Only switch to SPY if QQQ down >15%
        self.qqq_bias = 0.002  # CHATTY ENHANCEMENT 1: Dynamic QQQ overweighting
        
        # CHATTY ENHANCEMENT 2: Momentum persistence filter
        self.last_target = None

        # Allocation strategy
        self.qqq_allocation = 1.0   # Full allocation to QQQ
        self.spy_allocation = 0.85  # Reduced allocation to SPY (defensive)

        self.current_holding = None
        self.total_switches = 0
        self.qqq_periods = 0
        self.spy_periods = 0

        self.start_value = 5000.0
        self.benchmark_start_prices = {}

        # REDUCED FREQUENCY: Weekly only (reduce transaction costs)
        self.schedule.on(self.date_rules.every(DayOfWeek.MONDAY), 
                        self.time_rules.after_market_open("SPY", 30), 
                        self.rebalance)
        
        self.schedule.on(self.date_rules.month_start(), 
                        self.time_rules.after_market_open("SPY", 10), 
                        self.monthly_report)

        self.log("=== QQQ-PRIMARY STRATEGY INITIALIZED ===")
        self.log("MAJOR CHANGES: Eliminated SHY, Strong QQQ bias, Weekly rotation only")
        self.log("CHATTY ENHANCEMENTS: Dynamic overweighting, persistence filter, strong override")
        self.log(f"QQQ Bias: +{self.qqq_bias:.1%} | Threshold: {self.momentum_threshold:.1%}")
        self.log(f"QQQ Allocation: {self.qqq_allocation:.0%} | SPY Allocation: {self.spy_allocation:.0%}")

    def on_warmup_finished(self):
        self.benchmark_start_prices = {
            'qqq': float(self.securities[self.qqq].price),
            'spy': float(self.securities[self.spy].price)
        }
        self.log(f"Benchmarks: QQQ ${self.benchmark_start_prices['qqq']:.2f}, SPY ${self.benchmark_start_prices['spy']:.2f}")

    def monthly_report(self):
        if self.is_warming_up or not self.benchmark_start_prices:
            return
        
        try:
            current_qqq = float(self.securities[self.qqq].price)
            current_spy = float(self.securities[self.spy].price)
            current_portfolio = float(self.portfolio.total_portfolio_value)

            qqq_return = (current_qqq / self.benchmark_start_prices['qqq']) - 1
            spy_return = (current_spy / self.benchmark_start_prices['spy']) - 1
            strategy_return = (current_portfolio / self.start_value) - 1

            alpha_vs_qqq = (strategy_return - qqq_return) * 100.0
            alpha_vs_spy = (strategy_return - spy_return) * 100.0

            # Track QQQ preference
            total_periods = self.qqq_periods + self.spy_periods
            qqq_percentage = (self.qqq_periods / total_periods * 100) if total_periods > 0 else 0

            self.log(f"=== {self.time.strftime('%Y-%m')} QQQ-PRIMARY PERFORMANCE ===")
            self.log(f"Strategy: {strategy_return:.1%} | QQQ: {qqq_return:.1%} | SPY: {spy_return:.1%}")
            self.log(f"Alpha vs QQQ: {alpha_vs_qqq:+.1f}% | Alpha vs SPY: {alpha_vs_spy:+.1f}%")
            self.log(f"QQQ Exposure: {qqq_percentage:.0f}% | SPY Exposure: {100-qqq_percentage:.0f}%")

            self.plot("Performance", "Strategy", 1 + strategy_return)
            self.plot("Performance", "QQQ", 1 + qqq_return)
            self.plot("Performance", "SPY", 1 + spy_return)
            self.plot("QQQ Exposure", "Percentage", qqq_percentage)

        except Exception as e:
            self.log(f"Monthly report error: {str(e)}")

    def rebalance(self):
        if self.is_warming_up:
            return
        
        try:
            self.log(f"=== QQQ-PRIMARY REBALANCE: {self.time.strftime('%Y-%m-%d')} ===")
            
            # Get momentum data
            qqq_hist = self.history(self.qqq, self.momentum_period + 1, Resolution.DAILY)['close']
            spy_hist = self.history(self.spy, self.momentum_period + 1, Resolution.DAILY)['close']

            if len(qqq_hist) < self.momentum_period + 1 or len(spy_hist) < self.momentum_period + 1:
                self.log("Insufficient history")
                return

            # Calculate momentum
            qqq_momentum = (qqq_hist[-1] - qqq_hist[0]) / qqq_hist[0]
            spy_momentum = (spy_hist[-1] - spy_hist[0]) / spy_hist[0]
            
            # CHATTY ENHANCEMENT 1: Apply dynamic QQQ overweighting
            qqq_score = qqq_momentum + self.qqq_bias
            spy_score = spy_momentum
            
            diff = qqq_score - spy_score

            self.log(f"Raw Momentum: QQQ {qqq_momentum:.3f} | SPY {spy_momentum:.3f}")
            self.log(f"Enhanced Scores: QQQ {qqq_score:.3f} (+{self.qqq_bias:.3f}) | SPY {spy_score:.3f}")
            self.log(f"Difference: {diff:.3f} (threshold: {self.momentum_threshold:.3f})")

            # QQQ-PRIMARY LOGIC with Chatty's enhancements
            target_symbol = None
            target_name = None
            allocation = None

            # CHATTY ENHANCEMENT 3: Hard threshold override for QQQ when both strong
            if qqq_score > 0.08 and spy_score > 0.08:
                target_symbol = self.qqq
                target_name = "QQQ"
                allocation = 1.0
                self.qqq_periods += 1
                self.log("CHATTY OVERRIDE: Both assets strong - full QQQ allocation")
                
            elif qqq_momentum < self.qqq_severe_weakness:
                # QQQ severely weak (>15% decline) - defensive SPY
                target_symbol = self.spy
                target_name = "SPY"
                allocation = self.spy_allocation
                self.spy_periods += 1
                self.log(f"DEFENSIVE: QQQ severely weak ({qqq_momentum:.1%}) - switch to SPY")
                
            elif abs(diff) < self.momentum_threshold:
                # Close call - DEFAULT TO QQQ (key change)
                target_symbol = self.qqq
                target_name = "QQQ"
                allocation = self.qqq_allocation
                self.qqq_periods += 1
                self.log(f"CLOSE CALL: Defaulting to QQQ (diff: {diff:.3f} < threshold)")
                
            elif qqq_score > spy_score:
                # QQQ clearly winning
                target_symbol = self.qqq
                target_name = "QQQ"
                allocation = self.qqq_allocation
                self.qqq_periods += 1
                self.log(f"QQQ WINNING: Clear momentum advantage")
                
            else:
                # SPY winning but only use reduced allocation
                target_symbol = self.spy
                target_name = "SPY"
                allocation = self.spy_allocation
                self.spy_periods += 1
                self.log(f"SPY WINNING: Reduced allocation strategy")

            # CHATTY ENHANCEMENT 2: Momentum persistence filter
            if self.last_target == target_symbol:
                self.log(f"PERSISTENCE FILTER: Holding {target_name} - consistent momentum")
                return
            
            # Update persistence tracker
            self.last_target = target_symbol

            # Skip if already holding target (additional check)
            if self.current_holding == target_name:
                self.log(f"HOLDING: {target_name} at {allocation:.0%} allocation")
                return

            # Execute rotation
            self.liquidate()
            quantity = self.calculate_order_quantity(target_symbol, allocation)

            if quantity != 0:
                self.market_order(target_symbol, quantity)
                self.current_holding = target_name
                self.total_switches += 1

                self.log(f"=== ROTATION #{self.total_switches} EXECUTED ===")
                self.log(f"NEW POSITION: {target_name} | Allocation: {allocation:.0%} | Shares: {quantity}")
                
                # Enhanced logging
                if target_name == "QQQ":
                    self.log("BULL MODE: Maximum QQQ exposure")
                else:
                    self.log("DEFENSIVE MODE: Temporary SPY protection")

                # Plot holdings
                self.plot("Holdings", "QQQ", 1 if target_name == "QQQ" else 0)
                self.plot("Holdings", "SPY", 1 if target_name == "SPY" else 0)
                self.plot("Allocation Level", "Current", allocation)
                
            else:
                self.log("ERROR: Calculated quantity is zero")

        except Exception as e:
            self.log(f"Rebalance error: {str(e)}")

    def on_order_event(self, order_event):
        if order_event.status == OrderStatus.FILLED:
            self.log(f"FILLED: {order_event.symbol} - {order_event.fill_quantity} shares @ ${order_event.fill_price:.2f}")

    def on_end_of_algorithm(self):
        final_value = float(self.portfolio.total_portfolio_value)
        strategy_return = (final_value / self.start_value) - 1

        if self.benchmark_start_prices:
            current_qqq = float(self.securities[self.qqq].price)
            current_spy = float(self.securities[self.spy].price)
            
            qqq_total_return = (current_qqq / self.benchmark_start_prices['qqq']) - 1
            spy_total_return = (current_spy / self.benchmark_start_prices['spy']) - 1
            
            alpha_vs_qqq = strategy_return - qqq_total_return
            alpha_vs_spy = strategy_return - spy_total_return

            # Calculate exposure statistics
            total_periods = self.qqq_periods + self.spy_periods
            qqq_exposure_pct = (self.qqq_periods / total_periods * 100) if total_periods > 0 else 0

            self.log("=== QQQ-PRIMARY FINAL RESULTS ===")
            self.log(f"Period: 15 years (2010-2024)")
            self.log(f"Starting Capital: $5,000")
            self.log("")
            self.log("=== PERFORMANCE COMPARISON ===")
            self.log(f"Strategy Return:  {strategy_return:.1%}")
            self.log(f"QQQ Buy & Hold:   {qqq_total_return:.1%}")
            self.log(f"SPY Buy & Hold:   {spy_total_return:.1%}")
            self.log(f"Alpha vs QQQ:     {alpha_vs_qqq:.1%}")
            self.log(f"Alpha vs SPY:     {alpha_vs_spy:.1%}")
            self.log("")
            self.log("=== QQQ-PRIMARY OPTIMIZATION RESULTS ===")
            self.log(f"Total Rotations: {self.total_switches}")
            self.log(f"QQQ Exposure: {qqq_exposure_pct:.1f}% of time")
            self.log(f"SPY Exposure: {100-qqq_exposure_pct:.1f}% of time")
            self.log(f"QQQ Bias Applied: +{self.qqq_bias:.1%} momentum advantage")
            self.log(f"Rotation Threshold: {self.momentum_threshold:.1%} (reduced frequency)")
            self.log("CHATTY ENHANCEMENTS: Dynamic overweight + persistence filter + strong override")
            self.log("")
            
            # Performance assessment
            if alpha_vs_qqq > -0.10:  # Within 10% of QQQ
                self.log("STRONG RESULT: Close to QQQ performance with risk management")
            elif alpha_vs_qqq > -0.20:  # Within 20% of QQQ
                self.log("DECENT RESULT: Reasonable tracking of QQQ with some protection")
            elif strategy_return > spy_total_return:
                self.log("MIXED RESULT: Beat SPY but significant QQQ lag")
            else:
                self.log("POOR RESULT: Need further QQQ optimization")

            self.log(f"Final Holding: {self.current_holding}")
            self.log("")
            self.log("=== QQQ-PRIMARY STRATEGY COMPLETE ===")
            self.log("Key Changes: Eliminated bonds, strong QQQ bias, weekly rotation")

        else:
            self.log(f"Strategy Return: {strategy_return:.1%}")
            self.log(f"Total Rotations: {self.total_switches}")

        self.log("=== BACKTEST COMPLETE ===")