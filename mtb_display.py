"""Bobcat MTB Display"""

import argparse
import asyncio
import io
import logging
import time
import zlib

import pygame
import treepoem
from asyncio_mqtt import Client
from PIL import EpsImagePlugin

DEFAULT_MQTT_HOSTNAME = "127.0.0.1"
DEFAULT_MQTT_TOPIC = "service/v1/Validate/reader"

RESOLUTION = WIDTH, HEIGHT = 480, 320
COLOUR_WHITE = 255, 255, 255


def mtb_display(screen, data, delay: float = 5.0) -> None:
    """Show MTB"""
    logging.info("Display %d bytes for %.1f seconds", len(data), delay)
    barcode_data = zlib.compress(data)
    image = generate_barcode(barcode_type="azteccode", data=barcode_data, options={})
    ticket_image = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
    screen.blit(
        ticket_image, ((WIDTH - image.size[0]) / 2, (HEIGHT - image.size[1]) / 2)
    )
    pygame.event.pump()
    pygame.display.update()
    pygame.event.pump()
    time.sleep(delay)
    screen.fill(COLOUR_WHITE)
    pygame.event.pump()
    pygame.display.update()
    pygame.event.pump()


def _format_code(barcode_type, data, options):
    """From treepoem 1.0.1, convert to Py3.5+"""
    return "<{data}> <{options}> <{barcode_type}> cvn".format(
        data=data.hex(),
        options=treepoem._format_options(options).encode().hex(),
        barcode_type=barcode_type.encode().hex(),
    )


def generate_barcode(barcode_type, data, options):
    """From treepoem 1.0.1, convert to Py3.5+"""
    code = _format_code(barcode_type, data, options)
    bbox_lines = treepoem._get_bbox(code)
    full_code = treepoem.EPS_TEMPLATE.format(
        bbox=bbox_lines, bwipp=treepoem.BWIPP, code=code
    )
    return EpsImagePlugin.EpsImageFile(io.BytesIO(full_code.encode("utf8")))


async def receive_mqtt(client, topic, screen, delay):
    """MQTT message receive loop"""
    await client.connect()
    await client.subscribe(topic)
    async with client.unfiltered_messages() as messages:
        async for message in messages:
            logging.debug("Got MQTT topic %s", message.topic)
            mtb_display(screen, message.payload, delay)


def main():
    """Main function"""

    parser = argparse.ArgumentParser(description="Bobcat MTB Display")

    parser.add_argument("mtb", metavar="mtb", nargs="*", help="Read MTB from file")
    parser.add_argument(
        "--delay", metavar="delay", default=1, type=float, help="MTB delay"
    )
    parser.add_argument(
        "--mqtt", dest="mqtt", action="store_true", help="Read MTB from MQTT"
    )
    parser.add_argument(
        "--hostname",
        dest="hostname",
        help="MQTT hostname",
        default=DEFAULT_MQTT_HOSTNAME,
    )
    parser.add_argument(
        "--topic", dest="topic", help="MQTT topic", default=DEFAULT_MQTT_TOPIC
    )
    parser.add_argument(
        "--debug", dest="debug", action="store_true", help="Enable debugging"
    )

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    pygame.display.init()
    pygame.mouse.set_visible(0)
    screen = pygame.display.set_mode(RESOLUTION)
    screen.fill(COLOUR_WHITE)

    for input_filename in args.mtb:
        with open(input_filename, "rb") as input_file:
            mtbdata = input_file.read()
            mtb_display(screen, mtbdata, args.delay)

    if args.mqtt:
        client = Client(hostname=args.hostname)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(receive_mqtt(client, args.topic, screen, args.delay))
        loop.stop()


if __name__ == "__main__":
    main()
