import {expect} from '@playwright/test';
import type {Page,TestInfo} from '@playwright/test';

export async function captureTradeChart(page:Page,info:TestInfo,name:string){
  const chart=page.locator('.candles');
  await chart.scrollIntoViewIfNeeded();
  await page.mouse.move(0,0); // Keep hover/crosshair prices out of saved exit labels.
  const box=await chart.boundingBox();expect(box).not.toBeNull();
  expect(box!.height).toBe(350);
  const scroll=await page.evaluate(()=>({x:scrollX,y:scrollY}));
  const rect={x:box!.x+scroll.x,y:box!.y+scroll.y,width:box!.width,height:box!.height};
  // Installed Playwright1.65 Helper.enclosingIntRect encloses fractional CSS
  // coordinates (epsilon1e-3). A350px element can consequently produce351px.
  const width=Math.ceil(rect.x+rect.width-1e-3)-Math.floor(rect.x+1e-3);
  const height=Math.ceil(rect.y+rect.height-1e-3)-Math.floor(rect.y+1e-3);
  const png=await chart.screenshot({path:info.outputPath(name+'.png'),scale:'css'});
  expect(png.readUInt32BE(16)).toBe(width);expect(png.readUInt32BE(20)).toBe(height);
  return {...rect,expected_png_width:width,expected_png_height:height,scale:'css'};
}
