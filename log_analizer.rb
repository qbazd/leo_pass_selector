#!/usr/bin/env ruby 

require 'time'
require 'yaml'
require 'awesome_print'
require 'open3'
require 'fileutils'

def slot2pass(sat, sat_id, aoi_slot, pass_slot_margin)
	time_start = aoi_slot["time_slot"] 
	time_end = aoi_slot["time_slot"] + (aoi_slot["slots"] *60)
	slot_time = Time.at((((aoi_slot["time_slot"].to_i + aoi_slot["time_slot"].to_i + (( aoi_slot["slots"] )*60)) / 2) / 60) * 60).utc
	aoi_slot_range = time_start...time_end
	ext_slot_range = (time_start - (pass_slot_margin*60))...(time_end + (pass_slot_margin*60))
	return {sat: sat, sat_id: sat_id, ts: slot_time, aoi_range: aoi_slot_range, ext_range: ext_slot_range, aoi_cover: aoi_slot["aoi_cover"]}
end


def filter_avhrr_from_eumetcast(file)
	if file =~ /AVHR_HRP_00_M\d\d.*\.bz2/
		sat_id, ts_str = file.gsub(/.*_(M\d{2})_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d+)Z_/, "\\1;\\2-\\3-\\4 \\5:\\6:\\7+00").split(';')
		ts = Time.parse(ts_str).utc
		return yield(sat_id,ts,file)
	elsif file =~ /avhrr_.*noaa\d\d\.hrp\.bz2/ #avhrr_20150128_185600_noaa19.hrp.bz2
		sat_id, ts_str = file.gsub(/.*avhrr_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d+)_(noaa\d\d)\.hrp\.bz2/, "\\7;\\1-\\2-\\3 \\4:\\5:\\6+00").split(';')
		ts = Time.parse(ts_str).utc
		return yield(sat_id,ts,file)
	else
		return nil
	end
end

@day = nil
if ARGV[0] == "today"
	@day = Time.parse(Time.now.utc.strftime("%Y-%m-%d") + " 00:00:00+00").utc
elsif ARGV[1] == "day" && ARGV[0] =~ /^-\d+$/
	@day = Time.parse(Time.now.utc.strftime("%Y-%m-%d") + " 00:00:00+00").utc + (24 * 3600 * ARGV[0].to_i)
elsif ARGV[0] =~ /^(\d{4})-(\d{2})-(\d{2})$/
	@day = Time.parse(ARGV[0] + " 00:00:00+00").utc
else
	puts "usage:\n#{__FILE__} today"
	puts "usage:\n#{__FILE__} -# day"
	puts "usage:\n#{__FILE__} YYYY-MM-DD"
	exit 1
end

@force_cleanup = (ARGV.last == "force_cleanup")

ap @day

@sats = { "METOP-A" => "M02", "METOP-B" => "M01", "NOAA 19" => "noaa19"}

@pass_percentage = 75.0
@pass_slot_margin = 5
@pass_nrt_wait = 135 * 60 # 2:15

@predctions_directory = "./predictions"

@tmp_dir = "tmp"

passes_fn = @predctions_directory + "/" + @day.strftime("%Y%m%d")+"_000000-sb-avhrr-passes.yaml"
tles_fn = @predctions_directory + "/" + @day.strftime("%Y%m%d")+"_000000-avhrr.tle"

if !File.exists?(passes_fn)
	cmd = "./predict_passes.py --day #{@day.strftime("%Y-%m-%d")}"
	ap cmd
	o,e,s = Open3.capture3(cmd)
	raise "Predictor failed to predict '#{cmd}'\n#{e}" unless s.success? 
end

@day_passes = YAML.load_file(passes_fn)

@tles = {}

File.readlines(tles_fn).each_slice(3){|sat,l1,l2| @tles[sat.strip] = [l1.strip,l2.strip] }

sat_ids = Hash[@sats.to_a.map {|x| x=x.reverse}]

sat_files = {}

# get file listings 
Dir.glob("./log_analisis/E-UNS_-EARS____-AVHRR_______-DAILY_LOG-*").each{|file|
File.readlines(file).each{|line|
		f = line.split("|")[1]
		filter_avhrr_from_eumetcast(f){|sat_id,ts,file| 
			sat = sat_ids[sat_id]
			sat_files[sat] = {} if sat_files[sat].nil?
			sat_files[sat][ts] = [] if sat_files[sat][ts].nil?
			sat_files[sat][ts] << [file, 'none']
		}
	}
}
 
raise "no files" if sat_files.empty?

passes = @sats.map{|sat,sat_id| @day_passes[sat].map{|aoi_slot| slot2pass(sat, sat_id, aoi_slot, @pass_slot_margin) } }.flatten.sort{|a,b| a[:ts] <=> b[:ts] }

passes_already_done = 0

# select with procentage
passes.reject!{|pass| pass[:aoi_cover] < @pass_percentage }

passes.map{|pass|
	next if pass[:sat] == "METOP-B"

	next if pass[:aoi_cover] < @pass_percentage #do not show too small 

	puts "#{pass[:sat]} @ #{pass[:ts].strftime("%Y-%m-%d %H:%M:%S")} / #{"%.2f" % pass[:aoi_cover]}"

	pass_base = pass[:ts].strftime("%Y%m%d_%H%M%S-s_ug_eumetcast_avhrr")
	pass_base_path = pass[:ts].strftime("%Y/%m/%d")

	out_tar_fn = "#{pass_base}-hrpt.tar"
	out_tle_fn = "#{pass_base}-sat.tle"
	out_metadata_yaml_fn = "#{pass_base}-pass.yaml"

	pass_files = sat_files[pass[:sat]].select{|ts,files| pass[:ext_range].cover?(ts) }.map{|ts,files| [ts, *files.sample]}.sort{|a,b| a[0] <=> b[0] }

	aoi_range_slot_count = ((pass[:aoi_range].end - pass[:aoi_range].begin) / 60).to_i
	files_over_aoi_range_count = pass_files.select{|f| pass[:aoi_range].cover?(f[0]) }.count
	ext_range_slot_count = ((pass[:ext_range].end - pass[:ext_range].begin) / 60).to_i
	files_over_ext_range_count = pass_files.count

	puts "Files aoi:#{files_over_aoi_range_count}/#{aoi_range_slot_count}, ext:#{files_over_ext_range_count}/#{ext_range_slot_count}"

	if File.exists?("#{@tmp_dir}/#{pass_base_path}/#{out_metadata_yaml_fn}")
		puts "but already done :)"
		passes_already_done += 1
		next 
	end

	if  pass[:ext_range].end + @pass_nrt_wait > Time.now.utc
		puts "but not yet! #{"%.2f" % (((pass[:ext_range].end + @pass_nrt_wait) - Time.now.utc) / 60.0)}min to go"
		next
	end

	metadata = pass.dup
	meta_files = received_files.map{|f| {ts: f[0].utc, fn: f[1], remote_file: f[2], remote_host: f[3], mtime: f[4]}}
		
	metadata[:aoi_range_slot_count] = ((metadata[:aoi_range].end - metadata[:aoi_range].begin) / 60).to_i
	metadata[:files_over_aoi_range_count] = meta_files.select{|f| metadata[:aoi_range].cover?(f[:ts]) }.count
	metadata[:ext_range_slot_count] = ((metadata[:ext_range].end - metadata[:ext_range].begin) / 60).to_i
	metadata[:files_over_ext_range_count] = meta_files.count
	metadata[:last_received_file_mtime] = meta_files.map{|f| f[:mtime]}.max 
	metadata[:files] = meta_files

	#save tar

	# #write tle
	# File.open("#{@tmp_dir}/#{pass_base_path}/#{out_tle_fn}", "w") { |io| io.write "#{pass[:sat]}\n#{@tles[pass[:sat]][0]}\n#{@tles[pass[:sat]][1]}\n" ; io.close }

	# #save metadate
	# File.open("#{@tmp_dir}/#{pass_base_path}/#{out_metadata_yaml_fn}.tmp", "w") { |io| io.write metadata.to_yaml ; io.close }

	# #mv if ok
	# FileUtils.mv( "#{@tmp_dir}/#{pass_base_path}/#{out_metadata_yaml_fn}.tmp", "#{@tmp_dir}/#{pass_base_path}/#{out_metadata_yaml_fn}")

	#break
}
