const { chromium } = require('playwright');

async function testDeepDive() {
  console.log('🚀 Starting Deep Dive Test...');
  
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate directly to a specific opportunity
    console.log('📱 Navigating to specific opportunity...');
    await page.goto('http://localhost:3004/opportunities/predictive-maint-003');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    console.log('📄 Current page URL:', page.url());
    
    // Check if page loaded successfully
    const pageTitle = await page.title();
    console.log('📄 Page title:', pageTitle);

    // Look for Deep Dive button with multiple selectors
    console.log('🔍 Looking for Deep Dive button...');
    
    const selectors = [
      'button:has-text("Deep Dive")',
      'button[aria-label*="Deep Dive"]',
      'button >> text="Deep Dive"',
      'button:contains("Deep Dive")',
      '[data-testid="deep-dive-button"]'
    ];

    let deepDiveButton = null;
    for (const selector of selectors) {
      try {
        deepDiveButton = page.locator(selector);
        if (await deepDiveButton.count() > 0) {
          console.log(`✅ Found Deep Dive button with selector: ${selector}`);
          break;
        }
      } catch (e) {
        // Continue to next selector
      }
    }

    if (!deepDiveButton || await deepDiveButton.count() === 0) {
      console.log('❌ Deep Dive button not found. Searching page content...');
      const bodyText = await page.textContent('body');
      if (bodyText.includes('Deep Dive')) {
        console.log('✅ "Deep Dive" text found in page');
        // Try to find any element containing the text
        deepDiveButton = page.locator('*:has-text("Deep Dive")').last();
      } else {
        console.log('❌ "Deep Dive" text not found in page');
        console.log('Page content preview:', bodyText.substring(0, 800));
        return;
      }
    }

    // Test first click
    console.log('🎯 Testing first Deep Dive click...');
    await deepDiveButton.click();
    
    // Wait for response
    await page.waitForTimeout(2000);
    
    // Check for loading state
    let isLoading = false;
    const loadingSelectors = [
      'button:has-text("Analyzing...")',
      '.animate-spin',
      '[data-testid="loading"]'
    ];
    
    for (const selector of loadingSelectors) {
      if (await page.locator(selector).count() > 0) {
        isLoading = true;
        console.log(`✅ Loading state detected with: ${selector}`);
        break;
      }
    }

    if (isLoading) {
      console.log('✅ First click successful - loading state detected');
      
      // Wait for completion (max 30 seconds)
      console.log('⏳ Waiting for analysis to complete...');
      let completed = false;
      for (let i = 0; i < 30; i++) {
        await page.waitForTimeout(1000);
        const stillLoading = await page.locator('button:has-text("Analyzing...")').count() > 0;
        if (!stillLoading) {
          completed = true;
          break;
        }
        if (i % 5 === 0) console.log(`⏳ Still analyzing... (${i + 1}s)`);
      }
      
      if (completed) {
        console.log('✅ Analysis completed');
        
        // Test second click immediately
        console.log('🎯 Testing second Deep Dive click...');
        await deepDiveButton.click();
        await page.waitForTimeout(2000);
        
        const isLoadingSecond = await page.locator('button:has-text("Analyzing...")').count() > 0;
        if (isLoadingSecond) {
          console.log('✅ Second click successful');
        } else {
          console.log('❌ Second click failed - no loading state');
        }
      } else {
        console.log('⏰ Analysis timed out');
      }
    } else {
      console.log('❌ First click failed - no loading state detected');
      
      // Check for error messages
      const errorSelectors = [
        '[role="alert"]',
        '.error',
        '[data-sonner-toast]'
      ];
      
      for (const selector of errorSelectors) {
        const errorElements = await page.locator(selector);
        if (await errorElements.count() > 0) {
          const errorText = await errorElements.textContent();
          console.log('❌ Error detected:', errorText);
        }
      }
    }

    // Check for any toast notifications
    await page.waitForTimeout(1000);
    const toastElements = await page.locator('[data-sonner-toast]');
    if (await toastElements.count() > 0) {
      const toastText = await toastElements.textContent();
      console.log('📢 Toast notifications:', toastText);
    }

    // Look for results display anywhere on the page
    console.log('🔍 Checking for results display...');
    const resultKeywords = ['workflow', 'analysis', 'market research', 'competitive', 'results'];
    const bodyText = await page.textContent('body');
    
    let resultsFound = false;
    for (const keyword of resultKeywords) {
      if (bodyText.toLowerCase().includes(keyword)) {
        console.log(`✅ Found result keyword: "${keyword}"`);
        resultsFound = true;
      }
    }
    
    if (!resultsFound) {
      console.log('❌ No analysis results displayed in UI');
    }

    // Keep browser open for manual inspection
    console.log('🔍 Keeping browser open for 10 seconds for manual inspection...');
    await page.waitForTimeout(10000);

  } catch (error) {
    console.error('❌ Test failed:', error.message);
  } finally {
    await browser.close();
  }
}

testDeepDive().catch(console.error);