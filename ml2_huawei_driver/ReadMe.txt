�����뵼�롿
		ֱ����openstack havana neutron��neutron\plugins\ml2\driversĿ¼�£�
	�����Ŀ¼����
	
������˵����
1����controller�ڵ��/etc/default/neutron-server �ļ��޸�Ϊ NEUTRON_PLUGIN_CONFIG="/etc/neutron/plugins/ml2/ml2_conf.ini"
2��ע��huawei driver ���м���/usr/share/pyshared/neutron-2013.2.egg-info/entry_points.txt
	huawei = neutron.plugins.ml2.drivers.huawei.mechanism_huawei:HuaweiDriver
3����������/etc/neutron/plugins/ml2/ml2_conf.ini 
   mechanism_drivers = huawei
   vni_ranges = 4097:5000
