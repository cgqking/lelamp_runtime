# python
#!/usr/bin/env python

import argparse
import logging
import json
import time
from .follower import LeLampFollower, LeLampFollowerConfig
from .leader import LeLampLeader, LeLampLeaderConfig
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calibrate_follower(lamp_id: str, port: str) -> None:
    """Calibrate the follower robot."""
    logger.info(f"Starting follower calibration for lamp ID: {lamp_id} on port: {port}")

    follower_config = LeLampFollowerConfig(
        port=port,
        id=lamp_id,
    )

    follower = LeLampFollower(follower_config)

    try:
        follower.connect(calibrate=False)
        try:
            follower.calibrate()
            logger.info("Follower calibration completed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Follower calibration failed: invalid JSON response: {e}")
            logger.info("Retrying follower calibration once after reconnect...")
            try:
                if follower.is_connected:
                    follower.disconnect()
                time.sleep(0.5)
                follower.connect(calibrate=False)
                follower.calibrate()
                logger.info("Follower calibration completed successfully on retry")
            except Exception as retry_exc:
                logger.error(f"Follower calibration retry failed: {retry_exc}")
                raise
    except Exception as e:
        logger.error(f"Follower calibration failed: {e}")
        raise
    finally:
        if follower.is_connected:
            follower.disconnect()


def calibrate_leader(lamp_id: str, port: str) -> None:
    """Calibrate the leader robot."""
    logger.info(f"Starting leader calibration for lamp ID: {lamp_id} on port: {port}")

    leader_config = LeLampLeaderConfig(
        port=port,
        id=lamp_id,
    )

    leader = LeLampLeader(leader_config)

    try:
        leader.connect(calibrate=False)
        try:
            leader.calibrate()
            logger.info("Leader calibration completed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Leader calibration failed: invalid JSON response: {e}")
            logger.info("Retrying leader calibration once after reconnect...")
            try:
                if leader.is_connected:
                    leader.disconnect()
                time.sleep(0.5)
                leader.connect(calibrate=False)
                leader.calibrate()
                logger.info("Leader calibration completed successfully on retry")
            except Exception as retry_exc:
                logger.error(f"Leader calibration retry failed: {retry_exc}")
                raise
    except Exception as e:
        logger.error(f"Leader calibration failed: {e}")
        raise
    finally:
        if leader.is_connected:
            leader.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Calibrate LeLamp robot follower and leader sequentially")
    parser.add_argument('--id', type=str, required=True, help='ID of the lamp')
    parser.add_argument('--port', type=str, required=True, help='Serial port for the lamp')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--follower-only', dest='follower_only', action='store_true', help='Only run follower calibration')
    group.add_argument('--leader-only', dest='leader_only', action='store_true', help='Only run leader calibration')
    args = parser.parse_args()

    try:
        if args.follower_only:
            print("\n" + "="*50)
            print("FOLLOWER CALIBRATION (only)")
            print("="*50)
            calibrate_follower(args.id, args.port)
        elif args.leader_only:
            print("\n" + "="*50)
            print("LEADER CALIBRATION (only)")
            print("="*50)
            calibrate_leader(args.id, args.port)
        else:
            print("\n" + "="*50)
            print("FOLLOWER CALIBRATION")
            print("="*50)
            calibrate_follower(args.id, args.port)

            print("\n" + "="*50)
            print("LEADER CALIBRATION")
            print("="*50)
            calibrate_leader(args.id, args.port)

        print("\n" + "="*50)
        print("CALIBRATION COMPLETED SUCCESSFULLY")
        print("="*50)

    except Exception as e:
        logger.error(f"Calibration process failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())