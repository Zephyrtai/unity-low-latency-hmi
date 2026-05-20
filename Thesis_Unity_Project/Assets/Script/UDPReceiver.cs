using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

/// <summary>
/// 
/// </summary>
[Serializable] //To make data can be packaged
public class SensorData
{
    public float speed;
    public float raw_distance;
} 

public class UDPReceiver : MonoBehaviour
{
    Thread receiveThread;
    UdpClient client;
    public int port = 5005;
    private bool isRunning = true;

    private void Start()
    {
        if (receiveThread != null && receiveThread.IsAlive)
        {
            Debug.LogWarning("Receiver is already running.");
            return;
        }
        //1. Create a new Thread to execute
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        //2. Set background mode to prevent from being unable to close
        receiveThread.IsBackground = true; //The default is foreground thread
        //3. Start thread
        receiveThread.Start();
        Debug.Log("UDP Receiver started.");
    }
    private void ReceiveData()
    {  //1. Create client
        if (client == null) client = new UdpClient(port);
        /* 允许端口复用（避免偶发冲突） */
        /* client.Client.SetSocketOption(
           SocketOptionLevel.Socket,  //表示要设置的是 通用的套接字层级选项。
           SocketOptionName.ReuseAddress,  //选项名称, 允许“多个程序同时听同一个端口”
            true  //启用功能 ); 
        放在 Bind() 前面。*/
        while (isRunning)
        {
            try 
            {  //2. Ready to receive data
                IPEndPoint anyIP = new IPEndPoint(IPAddress.Any, 0); //Create to record (sender's)'IPAddress' and 'port'
                byte[] data = client.Receive(ref anyIP);//【ref】:当数据包到达时，Receive 方法不仅会把数据拿回来，还会把sender的真实 IP 和port写进 anyIP 里
            //阻塞等待（死等）：这行代码运行到这里会“卡住”，直到真的有人给你发了一个 UDP 包。如果没人发数据，程序就会一直停在这里等

               //3. Parse 解析
                string text = Encoding.UTF8.GetString(data);//Serder serializable data,correspondingly parse the data to read
               //4. read data
                SensorData sensor = JsonUtility.FromJson<SensorData>(text);
                Debug.Log($"speed: {sensor.speed} | raw distance: {sensor.raw_distance}");
            }
            catch (SocketException e)
            {  // 重点：当 Socket 被关闭时，这里会接住那个 0x80004005 报错
                if (isRunning) Debug.LogWarning($"UDP receive exception {e.Message}");
                else Debug.Log("UDP has been shutdown normally.");
            }
            catch (Exception err)
            {
                Debug.LogError(err.ToString());
            }
        }
    }

    private void OnApplicationQuit() //【message】(Unity)生命周期
    {   
        isRunning = false;// Stop receiving data(until next time start up)

        //1. if client exists, close it for releasing port to prevent errors caused by the port being occupaid
        if (client != null) {
            client.Close();
            client = null;
        }
        //2. If thread exists, `.Join()` wait for the thread to finish normally
        if (receiveThread != null) {
            receiveThread.Join();
            receiveThread = null; //Fully release upon exit(to avoid conflicts next time)
        }
    }
}
