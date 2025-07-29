const { chromium } = require('playwright');

async function testUpdatedDeepDive() {
  console.log('🚀 Starting Updated Deep Dive Test...');
  
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to opportunity
    console.log('📱 Navigating to opportunity...');
    await page.goto('http://localhost:3004/opportunities/predictive-maint-003');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Check for Deep Dive button
    console.log('🔍 Looking for updated Deep Dive button...');
    const deepDiveButton = page.locator('[data-testid="deep-dive-button"]');
    
    if (await deepDiveButton.count() === 0) {
      console.log('❌ Deep Dive button not found');
      return;
    }

    console.log('✅ Found Deep Dive button with test ID');

    // Test first click
    console.log('🎯 Testing first Deep Dive click...');
    await deepDiveButton.click();
    
    // Wait for loading state
    await page.waitForTimeout(2000);
    
    const isAnalyzing = await page.locator('button:has-text("Analyzing...")').count() > 0;
    if (isAnalyzing) {
      console.log('✅ First click successful - button shows "Analyzing..."');
      
      // Check for workflow ID display
      const workflowInfo = await page.locator('text=/Workflow:.*wf_plan_/').count();
      if (workflowInfo > 0) {
        console.log('✅ Workflow ID displayed in UI');
      }
      
      // Wait for completion with longer timeout
      console.log('⏳ Waiting for analysis to complete (max 60 seconds)...');
      let completed = false;
      
      for (let i = 0; i < 60; i++) {
        await page.waitForTimeout(1000);
        
        // Check if results appeared
        const resultsSection = await page.locator('[data-testid="deep-dive-results"]').count();
        if (resultsSection > 0) {
          console.log('✅ Results section appeared!');
          completed = true;
          break;
        }
        
        // Check if still analyzing
        const stillAnalyzing = await page.locator('button:has-text("Analyzing...")').count() > 0;
        if (!stillAnalyzing) {
          console.log('⚠️ Analysis stopped but checking for results...');
          await page.waitForTimeout(2000);
          break;
        }
        
        if (i % 10 === 0 && i > 0) {
          console.log(`⏳ Still analyzing... (${i}s)`);
        }
      }
      
      // Check for results display regardless of completion status
      await page.waitForTimeout(2000);
      const resultsSection = await page.locator('[data-testid="deep-dive-results"]');
      
      if (await resultsSection.count() > 0) {
        console.log('🎉 SUCCESS: Analysis results are displayed!');
        
        // Check for specific result components
        const marketResearch = await page.locator('text="Market Research"').count();
        const competitiveAnalysis = await page.locator('text="Competitive Analysis"').count();
        const marketSize = await page.locator('text="Total Addressable Market"').count();
        const competitors = await page.locator('text="Direct Competitors"').count();
        
        console.log(`📊 Market Research section: ${marketResearch > 0 ? '✅' : '❌'}`);
        console.log(`🏢 Competitive Analysis section: ${competitiveAnalysis > 0 ? '✅' : '❌'}`);
        console.log(`💰 Market Size data: ${marketSize > 0 ? '✅' : '❌'}`);
        console.log(`🏅 Competitor data: ${competitors > 0 ? '✅' : '❌'}`);
        
        // Test second click after results are displayed
        console.log('🎯 Testing second Deep Dive click...');
        const deepDiveButtonAfter = page.locator('[data-testid="deep-dive-button"]');
        
        const isDisabled = await deepDiveButtonAfter.isDisabled();
        if (isDisabled) {
          console.log('❌ Second click blocked: Button is disabled');
        } else {
          await deepDiveButtonAfter.click();
          await page.waitForTimeout(2000);
          
          const isAnalyzingAgain = await page.locator('button:has-text("Analyzing...")').count() > 0;
          if (isAnalyzingAgain) {
            console.log('✅ Second click successful - new analysis started');
          } else {
            console.log('❌ Second click failed - no new analysis started');
          }
        }
        
      } else {
        console.log('❌ No results displayed in UI');
        
        // Check for error messages
        const errorToasts = await page.locator('[data-sonner-toast]');
        if (await errorToasts.count() > 0) {
          const errorText = await errorToasts.textContent();
          console.log('❌ Error toast:', errorText);
        }
      }
      
    } else {
      console.log('❌ First click failed - no loading state detected');
    }

    // Keep browser open for manual inspection
    console.log('🔍 Keeping browser open for 15 seconds for manual inspection...');
    await page.waitForTimeout(15000);

  } catch (error) {
    console.error('❌ Test failed:', error.message);
  } finally {
    await browser.close();
  }
}

testUpdatedDeepDive().catch(console.error);