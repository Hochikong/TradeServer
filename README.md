TradeServer 0.2.2
=========
My trade server.


## Change log
- 0.2.2  
1.修复了空仓查询收益报错的bug  
2.修复了发出不存在的订单ID撤单请求，导致不正常返回的bug  
3.增加了Web控制台，方便用户监控交易记录  

- 0.2.1  
1.修复收益、成本计算的错误bug  
2.修复卖出部分股票时均价不变的错误  
3.修复均价计算错误的bug  
4.可以选择不同的撮合机制，config.ini的matching_mechanism若设为no，将不会等待真实股价符合撮合机制再撮合，而是直接成交，像雪球的模拟盈亏   


- 0.2：  
1.撮合服务器将用日志记录服务状态和交易记录，均保存在runtime目录下  
2.服务器不再管理用户每只股票从建仓到平仓的交易内容并统计收益，而是需要用户获取full_history自行处理   
3.修复了多用户查询实时收益时混入非自己持仓股票的bug  
4.订单撮合性能改进  
5.可以用maintainctl.py控制撮合服务的状态了

## Dependency
StockClib >= 0.3

## Usage
There are three tools you should use
- maintainctl.py: Use this tool to generate user, please check the instruction by entering 'help'
- run.py: Launch the REST API to communicate with trade server.
- omrun.py: Launch the TraderServer.

## Tips
1. If you want to delete a user, you should login to your database and 'kill' them by yourself.
2. Before the trade server launch, you should configure the 'ordermatch_service_coll' option and insert a document '{"status" : "run"}' in that collection. If you want to stop the server, first you should modify 'status' to 'stop' or something, then check the omserv_pid file in TradeStat directory and kill the server by pid number.
3. 不设交易时间限制，不设10%涨跌幅限制

## RESTful API
1. Create order: 
   - Header: trade_token
   - URL: /order
   - Method: POST 
   - Body: {"code":"000725","name":"京东方A","ops":"offer","amount":"200","price":"5.4"}  

   code: Must be a valid code   

   name: You should use the proper name   

   ops: 'offer' or 'bid'    

   amount: Amount, a string   

   price: Price, a string

2. Check remain order:
   - Header: trade_token
   - URL: /order
   - Method: GET
   - Body: None
   
3. Cancel order:
   - Header: trade_token
   - URL: /order
   - Method: POST
   - Body: {"ops":"cancel","order_id":"XRTlbCHcST"}
   
   ops: Must be 'cancel'
   
   order_id: The order id
   
4. Query users information:
   - Header: trade_token
   - URL: /user
   - Method: POST
   - Body: {"query":"full_history"}
   
   query: Specify what return you want to get: positions / full_history / profitstat(每6小时才会出一次结果) / user / real_time_profit

## Tips
REST API查询中，positions返回的totol是avgprice*amount,而real_time_profit的current_total才是实时市值  

在positions查询中返回的cost的内容是建仓至今佣金和税费的累加  


