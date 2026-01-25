using UnityEngine;
using System.Text;
using System.Net.Sockets;
using System.Net;
using System.Threading;

public class BioReceiver : MonoBehaviour
{
    // Make sure this says 5006 in the INSPECTOR too!
    public int port = 5006; 
    
    [Header("Live Data")]
    public float finalArousal; 
    public float sentiment;    

    [Header("Debug Info")]
    public string connectionStatus = "Not Started";
    public string lastPacket = "None";

    private UdpClient client;
    private Thread receiveThread;
    private bool isRunning = true;

    [System.Serializable]
    public class DataPacket
    {
        public float final_arousal; 
        public float sentiment;      
    }

    void Start()
    {
        // 1. Start the thread
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true;
        receiveThread.Start();
        
        Debug.Log($"<color=yellow>BioReceiver: Attempting to start on Port {port}...</color>");
    }

    private void ReceiveData()
    {
        try
        {
            // 2. Open the Port
            client = new UdpClient(port);
            client.Client.ReceiveTimeout = 500; // Timeout so we don't freeze
            IPEndPoint anyIP = new IPEndPoint(IPAddress.Any, 0);

            // If we get here, the port is OPEN and working!
            connectionStatus = $"Listening on {port}";
            Debug.Log($"<color=green>BioReceiver: SUCCESS! Listening on Port {port}</color>");

            while (isRunning)
            {
                try
                {
                    // 3. Wait for data
                    byte[] data = client.Receive(ref anyIP);
                    string text = Encoding.UTF8.GetString(data);
                    
                    // Update Debug Info
                    lastPacket = text; 
                    connectionStatus = "Receiving Data";

                    // 4. Parse
                    DataPacket packet = JsonUtility.FromJson<DataPacket>(text);
                    finalArousal = packet.final_arousal;
                    sentiment = packet.sentiment;
                }
                catch (SocketException) 
                { 
                    // This happens every 500ms if no data comes in. Normal behavior.
                } 
                catch (System.Exception ex)
                {
                    Debug.LogWarning("JSON Parse Error: " + ex.Message);
                }
            }
        }
        catch (System.Exception e)
        {
            // 5. IF YOU SEE THIS, THE PORT IS BLOCKED OR BUSY
            connectionStatus = "ERROR: Port Busy";
            Debug.LogError($"<color=red>BioReceiver FAILED: Could not open Port {port}. Is another Unity script using it?</color>");
        }
    }

    void OnApplicationQuit()
    {
        isRunning = false;
        if (client != null) client.Close();
        if (receiveThread != null) receiveThread.Abort();
    }
}