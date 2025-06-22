"""
Cloud persistence performance monitor.
Monitors cookie and session persistence performance in Streamlit Cloud.
"""

import streamlit as st
import time
import json
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CloudPersistenceMonitor:
    """Monitor session persistence performance in cloud environment."""

    def __init__(self):
        self.metrics = {
            "cookie_init_attempts": 0,
            "cookie_init_successes": 0,
            "cookie_save_attempts": 0,
            "cookie_save_successes": 0,
            "session_restore_attempts": 0,
            "session_restore_successes": 0,
            "localStorage_attempts": 0,
            "localStorage_successes": 0,
            "start_time": time.time()
        }

        # Load existing metrics from session state
        if "persistence_metrics" in st.session_state:
            stored_metrics = st.session_state.persistence_metrics
            self.metrics.update(stored_metrics)

    def record_cookie_init_attempt(self, success: bool = False):
        """Record cookie initialization attempt."""
        self.metrics["cookie_init_attempts"] += 1
        if success:
            self.metrics["cookie_init_successes"] += 1
        self._save_metrics()

        logger.info(
            f"Cookie init attempt: {success}, total attempts: {self.metrics['cookie_init_attempts']}")

    def record_cookie_save_attempt(self, success: bool = False):
        """Record cookie save attempt."""
        self.metrics["cookie_save_attempts"] += 1
        if success:
            self.metrics["cookie_save_successes"] += 1
        self._save_metrics()

        logger.info(
            f"Cookie save attempt: {success}, total attempts: {self.metrics['cookie_save_attempts']}")

    def record_session_restore_attempt(self, success: bool = False):
        """Record session restore attempt."""
        self.metrics["session_restore_attempts"] += 1
        if success:
            self.metrics["session_restore_successes"] += 1
        self._save_metrics()

        logger.info(
            f"Session restore attempt: {success}, total attempts: {self.metrics['session_restore_attempts']}")

    def record_localStorage_attempt(self, success: bool = False):
        """Record localStorage attempt."""
        self.metrics["localStorage_attempts"] += 1
        if success:
            self.metrics["localStorage_successes"] += 1
        self._save_metrics()

        logger.info(
            f"localStorage attempt: {success}, total attempts: {self.metrics['localStorage_attempts']}")

    def _save_metrics(self):
        """Save metrics to session state."""
        st.session_state.persistence_metrics = self.metrics

    def get_success_rates(self) -> Dict[str, float]:
        """Calculate success rates for each persistence method."""
        rates = {}

        # Cookie initialization success rate
        if self.metrics["cookie_init_attempts"] > 0:
            rates["cookie_init_rate"] = (
                self.metrics["cookie_init_successes"] /
                self.metrics["cookie_init_attempts"]
            ) * 100
        else:
            rates["cookie_init_rate"] = 0

        # Cookie save success rate
        if self.metrics["cookie_save_attempts"] > 0:
            rates["cookie_save_rate"] = (
                self.metrics["cookie_save_successes"] /
                self.metrics["cookie_save_attempts"]
            ) * 100
        else:
            rates["cookie_save_rate"] = 0

        # Session restore success rate
        if self.metrics["session_restore_attempts"] > 0:
            rates["session_restore_rate"] = (
                self.metrics["session_restore_successes"] /
                self.metrics["session_restore_attempts"]
            ) * 100
        else:
            rates["session_restore_rate"] = 0

        # localStorage success rate
        if self.metrics["localStorage_attempts"] > 0:
            rates["localStorage_rate"] = (
                self.metrics["localStorage_successes"] /
                self.metrics["localStorage_attempts"]
            ) * 100
        else:
            rates["localStorage_rate"] = 0

        return rates

    def display_metrics(self):
        """Display persistence metrics in Streamlit."""
        if not st.secrets.get("debug_mode", False):
            return

        with st.expander("📊 Persistence Performance Metrics", expanded=False):
            st.write("**Session Duration:**",
                     f"{(time.time() - self.metrics['start_time'])/60:.1f} minutes")

            # Success rates
            rates = self.get_success_rates()

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Cookie Performance:**")
                st.write(
                    f"- Init Rate: {rates['cookie_init_rate']:.1f}% ({self.metrics['cookie_init_successes']}/{self.metrics['cookie_init_attempts']})")
                st.write(
                    f"- Save Rate: {rates['cookie_save_rate']:.1f}% ({self.metrics['cookie_save_successes']}/{self.metrics['cookie_save_attempts']})")

            with col2:
                st.write("**Session Performance:**")
                st.write(
                    f"- Restore Rate: {rates['session_restore_rate']:.1f}% ({self.metrics['session_restore_successes']}/{self.metrics['session_restore_attempts']})")
                st.write(
                    f"- localStorage Rate: {rates['localStorage_rate']:.1f}% ({self.metrics['localStorage_successes']}/{self.metrics['localStorage_attempts']})")

            # Overall health indicator
            overall_rate = sum(rates.values()) / len(rates) if rates else 0

            if overall_rate >= 80:
                st.success(
                    f"🟢 Overall Health: {overall_rate:.1f}% (Excellent)")
            elif overall_rate >= 60:
                st.warning(f"🟡 Overall Health: {overall_rate:.1f}% (Good)")
            else:
                st.error(f"🔴 Overall Health: {overall_rate:.1f}% (Poor)")

            # Reset button
            if st.button("🔄 Reset Metrics"):
                del st.session_state.persistence_metrics
                st.rerun()

    def log_performance_summary(self):
        """Log performance summary to logger."""
        rates = self.get_success_rates()
        session_duration = (time.time() - self.metrics['start_time']) / 60

        summary = {
            "session_duration_minutes": session_duration,
            "success_rates": rates,
            "raw_metrics": self.metrics,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(
            f"Persistence Performance Summary: {json.dumps(summary, indent=2)}")
        return summary


# Global monitor instance
_monitor_instance = None


def get_persistence_monitor() -> CloudPersistenceMonitor:
    """Get or create global persistence monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = CloudPersistenceMonitor()
    return _monitor_instance


# Convenience functions for easy use
def record_cookie_init(success: bool):
    """Record cookie initialization attempt."""
    get_persistence_monitor().record_cookie_init_attempt(success)


def record_cookie_save(success: bool):
    """Record cookie save attempt."""
    get_persistence_monitor().record_cookie_save_attempt(success)


def record_session_restore(success: bool):
    """Record session restore attempt."""
    get_persistence_monitor().record_session_restore_attempt(success)


def record_localStorage(success: bool):
    """Record localStorage attempt."""
    get_persistence_monitor().record_localStorage_attempt(success)


def show_performance_metrics():
    """Display performance metrics."""
    get_persistence_monitor().display_metrics()


def log_performance():
    """Log performance summary."""
    return get_persistence_monitor().log_performance_summary()
