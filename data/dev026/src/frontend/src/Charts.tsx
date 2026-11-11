import {useEffect,useRef,useState} from 'react';
import {createChart,CandlestickSeries,createSeriesMarkers,ColorType} from 'lightweight-charts';
import type {UTCTimestamp,SeriesMarker,AutoscaleInfo} from 'lightweight-charts';
import {ResponsiveContainer,AreaChart,Area,XAxis,YAxis,Tooltip,CartesianGrid,ReferenceLine} from 'recharts';

export function Candles({bars,trade}:{bars:any[],trade?:any}){
  const host=useRef<HTMLDivElement>(null);
  const [fitLevels,setFitLevels]=useState(true);
  useEffect(()=>{
    if(!host.current||!bars.length)return;
    const element=host.current;
    delete element.dataset.exitPrice;
    element.dataset.fitLevels=String(fitLevels);
    const chart=createChart(element,{width:element.clientWidth,height:350,layout:{background:{type:ColorType.Solid,color:'#101a2c'},textColor:'#a9bad1',attributionLogo:true},grid:{vertLines:{color:'#1c2940'},horzLines:{color:'#1c2940'}},timeScale:{timeVisible:true},localization:{locale:'en-US'}});
    const series=chart.addSeries(CandlestickSeries,{upColor:'#48cfbf',downColor:'#ee8e84',borderVisible:false,wickUpColor:'#48cfbf',wickDownColor:'#ee8e84'});
    const data=bars.map(b=>({time:Math.floor(Date.parse(b.timestamp)/1000) as UTCTimestamp,open:b.open,high:b.high,low:b.low,close:b.close}));
    series.setData(data);
    const plotted=series.data();
    element.dataset.barCount=String(plotted.length);
    element.dataset.firstBarTime=String(plotted[0]?.time??'');
    element.dataset.lastBarTime=String(plotted.at(-1)?.time??'');
    let visible:{from:number,to:number}|null=null;
    let stopPrice:number|undefined,targetPrice:number|undefined;
    if(trade){
      const at=(stamp:string)=>{const t=Date.parse(stamp)/1000;let i=0;for(let n=0;n<data.length;n++){if(data[n].time<=t)i=n;else break;}return i;};
      const entry=at(trade.entry_at),exit=at(trade.exit_at),factor=bars[entry].factor||1,endFactor=bars[exit].factor||1;
      stopPrice=trade.stop*endFactor;targetPrice=trade.target*endFactor;
      const markers:SeriesMarker<UTCTimestamp>[]=[{time:data[entry].time,position:trade.side===1?'belowBar':'aboveBar',color:'#62dce5',shape:trade.side===1?'arrowUp':'arrowDown',text:'Entry'},
        {time:data[exit].time,position:'inBar',color:'#f3f7fc',shape:'circle',text:''}];
      createSeriesMarkers(series,markers.sort((a,b)=>Number(a.time)-Number(b.time)));
      for(const [price,title,color] of [[trade.entry_price*factor,'Entry','#62dce5'],[trade.stop*endFactor,'Stop','#ee8e84'],[trade.target*endFactor,'Target','#e7b35d'],[trade.exit_price*endFactor,'Exit','#f3f7fc']] as [number,string,string][]){if(Number.isFinite(price)){const line=series.createPriceLine({price,title,color,lineWidth:1,lineStyle:title==='Exit'?0:2,axisLabelVisible:true});if(title==='Exit')element.dataset.exitPrice=String(line.options().price);}}
      if(fitLevels){
        const levels=[trade.entry_price*factor,stopPrice,targetPrice,trade.exit_price*endFactor].filter(Number.isFinite) as number[];
        series.applyOptions({autoscaleInfoProvider:(original:()=>AutoscaleInfo|null)=>{
          const base=original();
          if(!levels.length)return base;
          return {...(base||{}),priceRange:{minValue:Math.min(...levels,base?.priceRange?.minValue??Infinity),maxValue:Math.max(...levels,base?.priceRange?.maxValue??-Infinity)}};
        }});
      }
      visible={from:Math.max(0,entry-25),to:Math.min(data.length-1,exit+20)};
    }
    const resize=()=>{chart.resize(element.clientWidth,350);if(visible)chart.timeScale().setVisibleLogicalRange(visible);else chart.timeScale().fitContent();
      const actual=chart.timeScale().getVisibleLogicalRange();element.dataset.visibleFrom=String(actual?.from??'');element.dataset.visibleTo=String(actual?.to??'');element.dataset.tradeId=trade?.id||'';
      element.dataset.stopY=stopPrice===undefined?'':String(series.priceToCoordinate(stopPrice)??'');
      element.dataset.targetY=targetPrice===undefined?'':String(series.priceToCoordinate(targetPrice)??'');};
    resize();const observer=new ResizeObserver(resize);observer.observe(element);
    const frame=requestAnimationFrame(resize);
    return()=>{observer.disconnect();cancelAnimationFrame(frame);chart.remove();};
  },[bars,trade,fitLevels]);
  return <div>{trade&&<label className="check chart-range"><input type="checkbox" checked={fitLevels} onChange={e=>setFitLevels(e.target.checked)}/>Fit all trade levels</label>}<div className="candles" ref={host} role="img" aria-label="Historical candlestick chart with saved trade markers"/>{!bars.length&&<p className="empty">Choose an explicit preview window or saved trade report to see prices.</p>}<p className="caption">Chart: causal split-normalized prices. Trade ledger: raw tradable prices. Times shown in UTC. <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">Charts by TradingView</a>.</p></div>;
}

export function Equity({rows,capital}:{rows:any[],capital:number}){
  if(!rows.length)return <p className="empty">No saved equity observations.</p>;
  return <div className="equity-chart" role="img" aria-label="Daily marked account equity"><ResponsiveContainer width="100%" height={265}><AreaChart data={rows} margin={{top:12,right:16,bottom:5,left:12}}><CartesianGrid stroke="#23314a" vertical={false}/><XAxis dataKey="date" stroke="#91a2bb" minTickGap={65}/><YAxis stroke="#91a2bb" domain={['auto','auto']} tickFormatter={v=>'$'+Number(v).toLocaleString()}/><Tooltip contentStyle={{background:'#111e32',border:'1px solid #34435a',color:'#e4eaf2'}} formatter={(v:any)=>'$'+Number(v).toFixed(2)}/><ReferenceLine y={capital} stroke="#aa8857" strokeDasharray="4 4"/><Area dataKey="equity" stroke="#62dce5" fill="#173844" fillOpacity={.8} isAnimationActive={false}/></AreaChart></ResponsiveContainer></div>;
}
