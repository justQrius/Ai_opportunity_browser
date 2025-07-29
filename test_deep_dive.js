const { chromium } = require('playwright');

async function testDeepDive() {
  console.log('🚀 Starting Deep Dive Test...');
  
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to the opportunities page
    console.log('📱 Navigating to opportunities page...');
    await page.goto('http://localhost:3004/opportunities');
    await page.waitForLoadState('networkidle');

    // Find the first opportunity card
    console.log('🔍 Looking for opportunity cards...');
    const opportunityCard = await page.locator('[data-testid="opportunity-card"]').first();
    
    if (await opportunityCard.count() === 0) {
      console.log('❌ No opportunity cards found, trying alternative selector...');
      // Try to find any clickable opportunity element
      await page.waitForSelector('a[href*="/opportunities/"]', { timeout: 10000 });
      const opportunityLink = await page.locator('a[href*="/opportunities/"]').first();
      await opportunityLink.click();
    } else {
      await opportunityCard.click();
    }

    console.log('📄 Navigated to opportunity detail page...');
    await page.waitForLoadState('networkidle');

    // Look for Deep Dive button
    console.log('🔍 Looking for Deep Dive button...');
    const deepDiveButton = await page.locator('button:has-text("Deep Dive")').first();
    
    if (await deepDiveButton.count() === 0) {
      console.log('❌ Deep Dive button not found. Page content:');
      const pageContent = await page.textContent('body');
      console.log(pageContent.substring(0, 500) + '...');
      return;
    }

    // Test first click
    console.log('🎯 First Deep Dive click...');
    await deepDiveButton.click();
    
    // Wait for response and check for toast/loading state
    await page.waitForTimeout(2000);
    
    const isLoading = await page.locator('button:has-text("Analyzing...")').count();
    if (isLoading > 0) {
      console.log('✅ First click successful - button shows "Analyzing..."');
      
      // Wait for analysis to complete
      console.log('⏳ Waiting for analysis to complete...');
      await page.waitForSelector('button:has-text("Deep Dive")', { timeout: 30000 });
      console.log('✅ Analysis completed, button back to "Deep Dive"');
    } else {
      console.log('❌ First click may have failed - no loading state detected');
    }

    // Test second click
    console.log('🎯 Second Deep Dive click...');
    await page.waitForTimeout(1000);
    await deepDiveButton.click();
    
    await page.waitForTimeout(2000);
    const isLoadingSecond = await page.locator('button:has-text("Analyzing...")').count();
    if (isLoadingSecond > 0) {
      console.log('✅ Second click successful - button shows "Analyzing..."');
    } else {
      console.log('❌ Second click failed - no loading state detected');
    }

    // Check for any toast messages
    const toasts = await page.locator('[data-sonner-toaster]').textContent();
    if (toasts) {
      console.log('📢 Toast messages:', toasts);
    }

    // Look for results display
    console.log('🔍 Looking for results display...');
    const resultsSection = await page.locator('[data-testid="deep-dive-results"]').count();
    if (resultsSection > 0) {
      console.log('✅ Results section found');
    } else {
      console.log('❌ No results section found - results not displayed in UI');
    }

  } catch (error) {
    console.error('❌ Test failed:', error.message);
  } finally {
    await browser.close();
  }
}

testDeepDive().catch(console.error);