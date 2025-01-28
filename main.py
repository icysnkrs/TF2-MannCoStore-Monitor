import time
import cloudscraper
from playwright.async_api import async_playwright
import asyncio
import discord
import datetime
import random
import json

# Reading Unusuals from .json file
def readingProducts(file_path: str):
    try:
        with open(file_path, 'r') as unusuals:
            return json.load(unusuals)
    except Exception as e:
        print(f"Couldn't read products .json file {e}")
        return []

# Cleaning complete memory every 24h function
def clean_old_products(processed_items, max_age_hours = 24):
    now = datetime.datetime.now()
    return [
        item for item in processed_items
        if 'timestamp' in item and (now - datetime.datetime.fromisoformat(item['timestamp'])).total_seconds() <= max_age_hours * 3600
    ]
# Proxy BUILD for requests

proxy_cache = []
async def load_proxies(file_path):
    global proxy_cache
    try:
        with open(file_path, 'r') as file:
            proxy_cache = [line.strip() for line in file if line.strip()]
            print(f"Loaded {len(proxy_cache)} proxies from {file_path}")
    except FileNotFoundError:
        print(f"Fisierul '{file_path}' nu a fost gasit.")
        proxy_cache = []
    except Exception as e:
        print(f"Eroare: {e}")
        proxy_cache = []

async def get_random_proxy(file_path, format_type):
    global proxy_cache

    if not proxy_cache:
        await load_proxies(file_path)

    if not proxy_cache:
        print("No proxies available!")
        return None

    random_proxy = random.choice(proxy_cache)
    parts = random_proxy.split(':')
    if len(parts) != 4:
        print(f"Bad proxy format: {random_proxy}")
        return None

    host = parts[0] + ':' + parts[1]
    username = parts[2]
    password = parts[3]

    if format_type == "cloudscraper":
        return {
            'http': f"http://{username}:{password}@{host}",
            'https': f"http://{username}:{password}@{host}",
        }
    elif format_type == "playwright":
        return {
            'server': f'http://{host}',
            'username': f'{username}',
            'password': f'{password}'
        }
    else:
        print("Invalid format!")
        return None

# SCRAPER BUILD (MANNCO.STORE)  *** NEW UNUSUALS ***

mannCoScraperChannels = {
    "unusual-hats": 'INSERT DISCORD CHANNEL ID',
    "unusual-taunts": 'INSERT DISCORD CHANNEL ID',
    "auctions": 'INSERT DISCORD CHANNEL ID',
}

scraper = cloudscraper.create_scraper()
newUnusualUrlMannCoStore = "https://mannco.store/items/get?quality=Unusual&age=DESC&game=440"

async def scrapeMannCoStore():
    try:
        proxy = await get_random_proxy('proxies.txt', format_type='cloudscraper')
        newUnusualResponse = await asyncio.to_thread(scraper.get, newUnusualUrlMannCoStore , proxies = proxy)
        print(f"Scraping MannCoStore UNUSUALS... [{datetime.datetime.now()}]")
        if newUnusualResponse.status_code == 200:
            parsedNewUnusual = newUnusualResponse
            return parsedNewUnusual.json()
        else:
            print("Eroare la ScrapeMannCoStore")
    except Exception as e:
        print(f"Error Scraping with cloudscraper: {e}")
    finally:
        scraper.close()

async def send_periodic_messages_newUnusuals(hats, taunts):

    processed_items = readingProducts("new_unusuals.json")
    current_unusuals = processed_items[-50:] # Getting only last 50 items, the newest ones on first page

    def generate_item_ids(item):
        return f"{item['url']}-{item['pp']}-{item.get('effect', '')}-{item.get('name', '')}"

    async def clean_memory():  # Cleaning Memory from processed items.
        while True:
            print('CLEANING MEMORY...')
            nonlocal processed_items
            processed_items = clean_old_products(processed_items)
            print(f'MEMORY CLEANED: [{len(processed_items)}] products remained')
            await asyncio.sleep(86400) # after 24h

    asyncio.create_task(clean_memory())

    while True:
        try:

            # Scraping new items
            new_Unusuals = await scrapeMannCoStore()
            new_entries = [item for item in new_Unusuals if generate_item_ids(item) not in (generate_item_ids(i) for i in processed_items)] # new entries (.JSON order from 0 to 49)

            if len(new_entries) > 0:

                print(f'New entries! [{len(new_entries)}]')

                for item in reversed(new_entries):
                    processed_items.append(item)
                    current_unusuals.append(item)
                    item_name = item['name']
                    print(f'ADDED ITEM - {item_name}')
                    # Product details
                    newUnusualName = item['name']
                    newUnusualImage = f"https://steamcommunity-a.akamaihd.net/economy/image/{item['image']}"
                    newUnusualEffect = f"{item['effect']}"
                    tf2WikiEffect = str(item['effect']).replace("★ ", "").replace(" ", "_")
                    newUnusualPrice = item['pp'] / 100
                    newUnusualStock = item['nbb']

                    # Create Discord embed
                    embed = discord.Embed(
                        title=f"[NEW UNUSUAL!] {newUnusualName}",
                        url=f"https://mannco.store/item/{item['id']}",
                        color=0x9d00ff
                    )
                    embed.set_thumbnail(url=f"{newUnusualImage}")
                    embed.add_field(name="🔮 Effect", value=f"{newUnusualEffect}", inline=True)
                    embed.add_field(name="🏷️ Price", value=f"{newUnusualPrice}$", inline=True)
                    embed.add_field(name="⭐ Stock", value=f"{newUnusualStock}", inline=True)
                    embed.add_field(
                        name="",
                        value=f"[Show Unusual Effect](https://wiki.teamfortress.com/wiki/Unusual#/media/File:Unusual_{tf2WikiEffect}.png)",
                        inline=True
                    )
                    embed.set_footer(text="Mannco Store Monitor")
                    name = newUnusualName.split()
                    if f'{name[0] + " " + name[1]}' == 'Unusual Taunt:':
                        await taunts.send(embed=embed)
                    else:
                        await hats.send(embed=embed)

                if len(current_unusuals) > 50:
                    current_unusuals = current_unusuals[-50:]
                    print("POP!")

                # Save updated current_unusuals to JSON file
                with open("new_unusuals.json", "w") as unusual:
                    json.dump(current_unusuals, unusual, indent=4)

            await asyncio.sleep(10) # Monitor DELAY in seconds '10'

        except Exception as e:
            print(f"An error occurred during MannCoStore new unusuals fetching: {e}")
            await asyncio.sleep(5)

async def scrapeMannCoStoreAuctions():

    url = "https://mannco.store/auctions"
    proxy = await get_random_proxy('proxies.txt', format_type='playwright')
    auction_names = []
    auction_images = []
    auction_prices = []
    auction_nextbid = []
    auction_time = []
    auction_timestamps = []
    auction_ids = set()

    async with async_playwright() as p:

        browser = await p.chromium.launch(proxy = proxy)
        try:
            print(f"Scraping MannCoStore AUCTIONS... [{datetime.datetime.now()}][{proxy}]")
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={"width": 1280, "height": 720},
                java_script_enabled=True
            )
            page = await context.new_page()
            await page.goto(url, timeout=0)
            await page.wait_for_load_state("networkidle")
            response = await page.query_selector("#auctionsList") # Main for AUCTION list
            auction_items = response.query_selector_all(".auctions-item")
            for item in await auction_items:
                title = await item.query_selector(".auctions-item__title")
                if title:
                    auction_names.append(await title.text_content())

                src_image = await item.query_selector(".auctions-item__thumbnail")
                if src_image:
                    auction_images.append(await src_image.get_attribute("src"))

                nextBid = await item.query_selector(".auctions-item__amount")
                if nextBid:
                    auction_nextbid.append(await nextBid.text_content())

                price = await item.query_selector(".auctions-item__price")
                if price:
                    auction_prices.append(await price.text_content())

                countdown = await item.query_selector(".countdown")
                if countdown:
                    auction_time.append(await countdown.text_content())
                    unix_timestamp = await countdown.get_attribute("data-time")
                    if unix_timestamp:
                        auction_timestamps.append(int(unix_timestamp))
                auction_ids.add(await item.get_attribute("data-auctionid"))

            return auction_names, auction_images, auction_prices, auction_nextbid, auction_time, auction_ids, auction_timestamps
        finally:
            await browser.close()

async def send_periodic_messages_newAuctions(channel):
    notified_auctions = set() # 10 min alerts *It will ping when auction is <= 10 min before ending
    try:
        while True:

            newAuctionNames, newAuctionImages, newAuctionPrices, newAuctionNextBid, newAuctionTime,newAuctionIds, newAuctionTimeStamps = await scrapeMannCoStoreAuctions()

            current_time = int(time.time() * 1000)
            for index, unix_timestamp in enumerate(newAuctionTimeStamps):
                time_left_ms = unix_timestamp - current_time
                time_left_seconds = time_left_ms // 1000

                if 0 < time_left_seconds <= 5700 and list(newAuctionIds)[index] not in notified_auctions:
                    notified_auctions.add(list(newAuctionIds)[index])
                    embed = discord.Embed(title=f"⏰ [AUCTION ALERT!] {newAuctionNames[index]}", url="https://mannco.store/auctions", color=0xFF0000)
                    embed.set_thumbnail(url=f"{newAuctionImages[index]}")
                    embed.add_field(name="🏷️ Price", value=f"{newAuctionPrices[index]} **[ Bid -> {newAuctionNextBid[index]}]**", inline=True)
                    embed.add_field(name="⏰ Time Left", value=f"{time_left_seconds // 60} minutes and {time_left_seconds % 60} seconds", inline=True)
                    embed.set_footer(text="Mannco Store Monitor")
                    await channel.send(embed=embed)

            notified_auctions.update(newAuctionIds)
            await asyncio.sleep(10) # Delay in seconds

    except Exception as e:
        print(f"Error Scraping MannCoStore Auctions: {e}")
        await asyncio.sleep(5)

# # Setting up DISCORD BOT
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
@client.event
async def on_ready():

    print(f'MannCoStore bot started! 🚀')
    channelNewUnusualHats = client.get_channel(mannCoScraperChannels['unusual-hats'])
    channelNewUnusualTaunts = client.get_channel(mannCoScraperChannels['unusual-taunts'])

    if channelNewUnusualHats or channelNewUnusualTaunts:
        asyncio.create_task(send_periodic_messages_newUnusuals(channelNewUnusualHats, channelNewUnusualTaunts))
    await asyncio.sleep(3)

    channelNewAuctions = client.get_channel(mannCoScraperChannels['auctions'])

    if channelNewAuctions:
        asyncio.create_task(send_periodic_messages_newAuctions(channelNewAuctions))


client.run('Discord bot TOKEN')