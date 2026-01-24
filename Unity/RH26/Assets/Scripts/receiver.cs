using UnityEngine;
using System.Text;
using System.Net.Sockets;
using System.Net;
using System.Threading;

public class BioReceiver : MonoBehaviour
{
    public int port = 5015;

    // Generic names allow you to pipe ANY data here later (GSR, Stress, HRV, etc.)
    [Header("Streamed Data")]
    public float sensor_1;
    public float sensor_2;

    private UdpClient client;
    private Thread receiveThread;
    private bool isRunning = true;

    [System.Serializable]
    public class DataPacket
    {
        public float sensor_1;
        public float sensor_2;
    }

    void Start()
    {
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true;
        receiveThread.Start();
    }

    private void ReceiveData()
    {
        client = new UdpClient(port);
        IPEndPoint anyIP = new IPEndPoint(IPAddress.Any, 0);

        while (isRunning)
        {
            try
            {
                byte[] data = client.Receive(ref anyIP);
                string text = Encoding.UTF8.GetString(data);

                // Fast JSON parsing
                DataPacket packet = JsonUtility.FromJson<DataPacket>(text);

                sensor_1 = packet.sensor_1;
                sensor_2 = packet.sensor_2;
            }
            catch (System.Exception) { /* Handle disconnects */ }
        }
    }

    void OnApplicationQuit()
    {
        isRunning = false;
        if (client != null) client.Close();
        if (receiveThread != null) receiveThread.Abort();
    }
}