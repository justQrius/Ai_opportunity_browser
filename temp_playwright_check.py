import asyncio
from playwright.async_api import async_playwright, expect
import sys

async def main():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Use host.docker.internal to access the host machine from within the Docker container
        base_url = "http://host.docker.internal:3004"

        try:
            # 1. Navigate to the home page
            print("STEP 1: Navigating to the home page...")
            await page.goto(base_url, timeout=20000, wait_until='domcontentloaded')
            await expect(page.get_by_role("heading", name="AI Opportunities")).to_be_visible(timeout=15000)
            print("✅ SUCCESS: Home page loaded successfully.")
            results['home_page'] = 'Success'

        except Exception as e:
            print(f"❌ ERROR: Failed to load the home page. Details: {e}")
            results['home_page'] = f"Failed: {e}"
            await browser.close()
            sys.exit(1) # Exit if home page fails to load

        try:
            # 2. Check for the opportunity list
            print("\nSTEP 2: Checking for the opportunity list...")
            # Wait for either the list to appear or the empty/error state
            await page.wait_for_selector('[class*="OpportunityList_container"], [class*="EmptyState_container"], [class*="ErrorState_container"]', timeout=15000)

            opportunity_links = page.locator('a[href^="/opportunities/"]')
            count = await opportunity_links.count()

            if count > 0:
                print(f"✅ SUCCESS: Found {count} opportunities listed.")
                results['opportunity_list'] = f"Success, found {count} items."
            else:
                empty_state = page.get_by_text("No opportunities found")
                if await empty_state.is_visible():
                    print("⚠️ WARNING: The opportunity list is empty.")
                    results['opportunity_list'] = 'Warning: List is empty.'
                else:
                    error_state = page.get_by_text("Error loading opportunities")
                    if await error_state.is_visible():
                         print("❌ ERROR: An error message is displayed instead of the list.")
                         results['opportunity_list'] = 'Error: Error message displayed.'
                    else:
                         print("❌ ERROR: Could not determine the state of the opportunity list.")
                         results['opportunity_list'] = 'Error: Unknown state.'

        except Exception as e:
            print(f"❌ ERROR: Failed while checking for the opportunity list. Details: {e}")
            results['opportunity_list'] = f"Failed: {e}"


        # 3. Click on the first opportunity and check the detail page
        if results.get('opportunity_list', '').startswith('Success'):
            try:
                print("\nSTEP 3: Testing navigation to the detail page...")
                first_opportunity_link = page.locator('a[href^="/opportunities/"]').first
                href = await first_opportunity_link.get_attribute("href")
                await first_opportunity_link.click()
                
                await page.wait_for_url(f"**{href}", timeout=15000)
                print(f"✅ SUCCESS: Navigated to opportunity detail page: {page.url}")

                await expect(page.get_by_role("button", name="Back")).to_be_visible(timeout=10000)
                print("✅ SUCCESS: Opportunity detail page appears to be working correctly.")
                results['detail_page'] = 'Success'

            except Exception as e:
                print(f"❌ ERROR: Failed to navigate to or validate the detail page. Details: {e}")
                results['detail_page'] = f"Failed: {e}"
        else:
            print("\nSTEP 3: Skipping detail page check due to issues with the opportunity list.")
            results['detail_page'] = 'Skipped'

        await browser.close()

asyncio.run(main())