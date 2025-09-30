# Hi
cd E:\bigData\kafka 

.\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties

---------

cd E:\bigData\kafka

.\bin\windows\kafka-server-start.bat .\config\server.properties

---------

.\bin\windows\kafka-topics.bat --create --topic test --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

---------

Verify the topic exists:

.\bin\windows\kafka-topics.bat --list --bootstrap-server localhost:9092

-----------------

<!-- cd C:\Users\PC\Desktop\Coins
.\.venv\Scripts\Activate.ps1
python ingest_fx.py --loop --seconds 60


cd C:\Users\PC\Desktop\Coins
.\.venv\Scripts\Activate.ps1
streamlit run app.py -->
